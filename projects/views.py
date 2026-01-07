import os
import requests
from decimal import Decimal
from django.conf import settings
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.clickjacking import xframe_options_exempt  # Iframe uchun ruxsat
from django.contrib import messages
from django.db.models import Q, F
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from notifications.signals import notify

# --- FLUTTER API IMPORTLARI (MUHIM: Bularsiz xato beradi) ---
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from .serializers import ProjectSerializer, RegisterSerializer, ProfileSerializer

# MODELLAR
from .models import (
    Project, ProjectImage, Sync, Profile, CommunityMessage,
    Contact, Transaction, Deposit, Withdrawal
)
# FORMALAR
from .forms import ProjectForm, CommentForm, UserRegisterForm, UserUpdateForm, ProfileUpdateForm


# ==========================================
# 1. YORDAMCHI FUNKSIYALAR
# ==========================================
def get_code_snippet(project):
    """Manba kodi oynasi uchun qisqa preview (15 qator)"""
    if not project.source_code:
        return "// Kod yuklanmagan."
    try:
        with project.source_code.open('r') as f:
            content = f.read(1000)
            text = content.decode('utf-8', errors='ignore') if isinstance(content, bytes) else content
            return "\n".join(text.splitlines()[:15]) + "\n..."
    except Exception:
        return "// Kodni o'qib bo'lmadi."


# ==========================================
# 2. ASOSIY SAHIFA
# ==========================================
def home_page(request):
    search_query = request.GET.get('q', '')
    category_filter = request.GET.get('category', None)
    projects = Project.objects.filter(is_frozen=False)

    if search_query:
        projects = projects.filter(
            Q(category__icontains=search_query) |
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        ).distinct()
    if category_filter:
        projects = projects.filter(category=category_filter)

    return render(request, 'home.html', {
        'projects': projects.order_by('-views'),
        'categories': Project.CATEGORY_CHOICES,
        'search_query': search_query,
        'page_title': "Bosh sahifa - DevTube"
    })


# ==========================================
# 3. LOYIHA AMALLARI (CRUD & DETAIL)
# ==========================================
@login_required
def create_project(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES)
        if form.is_valid():
            p = form.save(commit=False)
            p.author = request.user
            p.save()
            for img in request.FILES.getlist('more_images'):
                ProjectImage.objects.create(project=p, image=img)
            messages.success(request, f"'{p.title}' yuklandi!")
            return redirect('home')
    else:
        form = ProjectForm()
    return render(request, 'create_project.html', {'form': form})


@login_required
def update_project(request, pk):
    p = get_object_or_404(Project, pk=pk)
    if request.user != p.author:
        messages.error(request, "Huquqingiz yo'q!")
        return redirect('home')
    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES, instance=p)
        if form.is_valid():
            form.save()
            messages.success(request, "Yangilandi!")
            return redirect('project_detail', pk=p.pk)
    return render(request, 'update_project.html', {'form': ProjectForm(instance=p), 'project': p})


@login_required
def delete_project(request, pk):
    p = get_object_or_404(Project, pk=pk)
    if request.user != p.author:
        return HttpResponseForbidden("Faqat muallif o'chira oladi.")
    if request.method == 'POST':
        p.delete()
        messages.warning(request, "O'chirildi.")
        return redirect('profile', username=request.user.username)
    return render(request, 'delete.html', {'project': p})


# --- ASOSIY PROJECT VIEW ---
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if project.is_frozen and request.user != project.author and not request.user.is_superuser:
        messages.error(request, "Loyiha muzlatilgan.")
        return redirect('home')

    Project.objects.filter(pk=pk).update(views=F('views') + 1)
    project.refresh_from_db()

    if request.method == 'POST' and request.user.is_authenticated:
        form = CommentForm(request.POST)
        if form.is_valid():
            c = form.save(commit=False)
            c.user, c.project = request.user, project
            c.save()
            if project.author != request.user:
                notify.send(request.user, recipient=project.author, verb='izoh qoldirdi', target=project)
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'username': c.user.username,
                    'avatar_url': c.user.profile.avatar.url if c.user.profile.avatar else '',
                    'body': c.body
                })
            return redirect('project_detail', pk=pk)

    code_preview = get_code_snippet(project)
    is_html_file = project.source_code and project.source_code.name.lower().endswith('.html')

    has_access = project.price == 0 or (request.user.is_authenticated and (
            request.user == project.author or project.buyers.filter(id=request.user.id).exists()))
    is_synced = request.user.is_authenticated and Sync.objects.filter(follower=request.user.profile,
                                                                      following=project.author.profile).exists()

    return render(request, 'project_detail.html', {
        'project': project, 'form': CommentForm(), 'code_preview': code_preview,
        'live_preview': is_html_file, 'has_bought': has_access, 'is_synced': is_synced
    })


# --- JONLI NATIJA UCHUN PROXY VIEW ---
@xframe_options_exempt
def live_project_view(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not project.source_code:
        return HttpResponse("Kod yo'q", content_type="text/plain")
    try:
        with project.source_code.open('r') as f:
            content = f.read()
            if isinstance(content, bytes):
                content = content.decode('utf-8', errors='ignore')
        return HttpResponse(content, content_type="text/html")
    except Exception as e:
        return HttpResponse(f"Xatolik: {e}", content_type="text/plain")


# ==========================================
# 4. IJTIMOIY & MOLIYA
# ==========================================
@login_required
def like_project(request, pk):
    if request.method == 'POST':
        p = get_object_or_404(Project, pk=pk)
        if request.user in p.likes.all():
            p.likes.remove(request.user)
            l = False
        else:
            p.likes.add(request.user)
            l = True
        if p.author != request.user:
            notify.send(request.user, recipient=p.author, verb='like bosdi', target=p)
        return JsonResponse({'total_likes': p.likes.count(), 'is_liked': l})
    return JsonResponse({'error': 'POST required'}, status=400)


@login_required
def save_project(request, pk):
    if request.method == 'POST':
        p = get_object_or_404(Project, pk=pk)
        if request.user in p.saved_by.all():
            p.saved_by.remove(request.user)
            s = False
        else:
            p.saved_by.add(request.user)
            s = True
        return JsonResponse({'is_saved': s})
    return JsonResponse({'error': 'POST required'}, status=400)


@login_required
def toggle_sync(request, username):
    if request.method == 'POST':
        t = get_object_or_404(User, username=username)
        p = request.user.profile
        if p == t.profile:
            return JsonResponse({'error': 'Self'}, status=400)
        obj = Sync.objects.filter(follower=p, following=t.profile)
        if obj.exists():
            obj.delete()
            s = False
        else:
            Sync.objects.create(follower=p, following=t.profile)
            s = True
            notify.send(request.user, recipient=t, verb='sinxronlashdi')
        return JsonResponse({'is_synced': s, 'followers_count': t.profile.followers.count()})
    return JsonResponse({'error': 'POST required'}, status=400)


@login_required
def buy_project(request, pk):
    p = get_object_or_404(Project, pk=pk)
    b = request.user.profile
    if p.is_frozen:
        messages.error(request, "Muzlatilgan.")
        return redirect('home')
    if request.user == p.author or p.buyers.filter(id=request.user.id).exists():
        return redirect('project_detail', pk=pk)
    if b.balance >= p.price:
        b.balance -= p.price
        b.save()
        p.author.profile.balance += p.price
        p.author.profile.save()
        p.buyers.add(request.user)
        Transaction.objects.create(user=request.user, project=p, amount=p.price, status=Transaction.COMPLETED)
        notify.send(request.user, recipient=p.author, verb='sotib oldi', target=p)
        messages.success(request, "Xarid qilindi!")
    else:
        messages.error(request, "Mablag' yetarli emas.")
        return redirect('add_funds')
    return redirect('project_detail', pk=pk)


@login_required
def report_project(request, pk):
    p = get_object_or_404(Project, pk=pk)
    Project.objects.filter(pk=pk).update(reports_count=F('reports_count') + 1)
    p.refresh_from_db()
    if p.reports_count >= 10 and not p.is_frozen:
        p.is_frozen = True
        p.save()
        notify.send(User.objects.filter(is_superuser=True).first(), recipient=p.author, verb='Bloklandi', target=p)
        messages.error(request, "Bloklandi.")
    else:
        messages.warning(request, "Shikoyat yuborildi.")
    return redirect('home')


# ==========================================
# 5. TOOLS & WALLET & PROFIL
# ==========================================
def online_compiler(request):
    res = ""
    if request.method == 'POST':
        src, lang = request.POST.get('code', ''), request.POST.get('language', 'python')
        try:
            r = requests.post("https://emkc.org/api/v2/piston/execute",
                              json={"language": lang, "version": "*", "files": [{"content": src}]}, timeout=10)
            data = r.json()
            res = data['run'].get('stdout', '') + "\n" + data['run'].get('stderr', '')
        except:
            res = "API Error"
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'result': res})
    return render(request, 'compiler.html', {'result': res,
                                             'languages': [('python', 'Python'), ('javascript', 'Node.js'),
                                                           ('cpp', 'C++'), ('java', 'Java')]})


def cpp_test(request):
    return online_compiler(request)


@login_required
def add_funds(request):
    if request.method == 'POST':
        Deposit.objects.create(user=request.user, amount=Decimal(request.POST.get('amount')),
                               receipt=request.FILES.get('receipt'), status=Deposit.PENDING)
        messages.success(request, "Chek yuborildi.")
        return redirect('profile')
    return render(request, 'add_funds.html')


@login_required
def withdraw_money(request):
    if request.method == 'POST':
        Withdrawal.objects.create(user=request.user, amount=Decimal(request.POST.get('amount')),
                                  card_number=request.POST.get('card_number'), status=Withdrawal.PENDING)
        messages.success(request, "So'rov yuborildi.")
        return redirect('profile')
    return render(request, 'withdraw.html')


def profile(request, username=None):
    if username:
        t = get_object_or_404(User, username=username)
        o = (request.user == t)
    else:
        if not request.user.is_authenticated:
            return redirect('login')
        t, o = request.user, True
    if request.method == 'POST' and o:
        u = UserUpdateForm(request.POST, instance=request.user)
        p = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if u.is_valid() and p.is_valid():
            u.save()
            p.save()
            messages.success(request, 'Yangilandi!')
            return redirect('profile', username=request.user.username)
    return render(request, 'profile.html', {'target_user': t, 'u_form': UserUpdateForm(instance=t),
                                            'p_form': ProfileUpdateForm(instance=t.profile),
                                            'projects': Project.objects.filter(author=t).order_by('-created_at'),
                                            'is_owner': o,
                                            'is_synced': request.user.is_authenticated and not o and Sync.objects.filter(
                                                follower=request.user.profile, following=t.profile).exists()})


@login_required
def community_chat(request):
    msgs = CommunityMessage.objects.all().order_by('-created_at')[:50]
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' and request.method == 'POST':
        if txt := request.POST.get('body'):
            CommunityMessage.objects.create(user=request.user, body=txt)
        return JsonResponse({'html': render_to_string('chat_messages_partial.html',
                                                      {'chat_messages': reversed(msgs), 'request': request})})
    return render(request, 'community_chat.html', {'chat_messages': reversed(msgs)})


@login_required
def my_notifications(request):
    request.user.notifications.mark_all_as_read()
    return render(request, 'notifications.html', {'notifications': request.user.notifications.all()})


@login_required
def syncing_projects(request):
    ids = [s.following.user.id for s in request.user.profile.following.all()]
    return render(request, 'syncing.html',
                  {'projects': Project.objects.filter(author__id__in=ids).order_by('-created_at')})


@login_required
def liked_videos(request):
    return render(request, 'home.html', {'projects': Project.objects.filter(likes=request.user)})


@login_required
def my_videos(request):
    return render(request, 'home.html', {'projects': Project.objects.filter(author=request.user)})


@login_required
def saved_projects(request):
    return render(request, 'home.html', {'projects': request.user.saved_projects.all()})


def trending(request):
    return render(request, 'home.html', {'projects': Project.objects.all().order_by('-views')})


def help_page(request):
    return render(request, 'help.html')


def announcements(request):
    return render(request, 'announcements.html')


def portfolio_page(request):
    return render(request, 'index.html')


def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Xush kelibsiz!")
            return redirect('login')
    return render(request, 'signup.html', {'form': UserRegisterForm()})


@login_required
def contact_page(request):
    if request.method == 'POST':
        Contact.objects.create(user=request.user, subject=request.POST.get('subject'),
                               message=request.POST.get('message'))
        messages.success(request, "Xabar yuborildi.")
        return redirect('contact')
    return render(request, 'contact.html')


# ==========================================
# 6. FLUTTER API (DRF) VIEWS - (MANA SHU YER XATOSIZ ISHLAYDI ENDI)
# ==========================================

# 1. REGISTRATSIYA
class RegisterAPI(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            "user": RegisterSerializer(user, context=self.get_serializer_context()).data,
            "token": token.key
        })

# 2. PROFILNI KO'RISH VA TAHRIRLASH
class ProfileAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = ProfileSerializer(request.user.profile)
        return Response(serializer.data)

    def put(self, request):
        serializer = ProfileSerializer(request.user.profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 3. LOYIHALAR RO'YXATI (List)
class ProjectListAPI(generics.ListAPIView):
    queryset = Project.objects.filter(is_frozen=False).order_by('-created_at')
    serializer_class = ProjectSerializer

# 4. LOYIHA YARATISH (Create)
class ProjectCreateAPI(generics.CreateAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

# 5. BITTA LOYIHA (Detail)
class ProjectDetailAPI(generics.RetrieveAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

# 6. LOYIHANI O'ZGARTIRISH/O'CHIRISH (Update/Delete)
class ProjectUpdateDeleteAPI(generics.RetrieveUpdateDestroyAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Faqat o'z loyihasini o'chira oladi
        return Project.objects.filter(author=self.request.user)