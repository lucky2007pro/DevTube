import os
import requests
from decimal import Decimal
from django.conf import settings
from django.db import transaction  # <--- MUHIM: Tranzaksiyalar uchun
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.clickjacking import xframe_options_exempt
from django.contrib import messages
from django.db.models import Q, F
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from notifications.signals import notify

# --- FLUTTER API IMPORTLARI ---
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.parsers import MultiPartParser, FormParser  # Rasmlar uchun
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
    """Manba kodi oynasi uchun qisqa preview"""
    if not project.source_code:
        return "// Kod yuklanmagan."
    try:
        project.source_code.open('r')
        content = project.source_code.read(1000)
        # Fayl yopishni avtomatik qilish uchun open ishlatildi, lekin storage da context manager har doim ham ishlamasligi mumkin
        # Shuning uchun oddiy read qilamiz.
        text = content.decode('utf-8', errors='ignore') if isinstance(content, bytes) else content
        project.source_code.close()  # Faylni yopish esdan chiqmasin
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
# 3. LOYIHA AMALLARI (WEB)
# ==========================================
@login_required
def create_project(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES)
        if form.is_valid():
            p = form.save(commit=False)
            p.author = request.user
            p.save()
            # Qo'shimcha rasmlarni saqlash
            for img in request.FILES.getlist('more_images'):
                ProjectImage.objects.create(project=p, image=img)
            messages.success(request, f"'{p.title}' muvaffaqiyatli yuklandi!")
            return redirect('home')
    else:
        form = ProjectForm()
    return render(request, 'create_project.html', {'form': form})


@login_required
def update_project(request, pk):
    p = get_object_or_404(Project, pk=pk)
    if request.user != p.author:
        messages.error(request, "Bu loyihani tahrirlash huquqiga ega emassiz!")
        return redirect('home')

    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES, instance=p)
        if form.is_valid():
            form.save()
            messages.success(request, "Loyiha yangilandi!")
            return redirect('project_detail', pk=p.pk)
    else:
        form = ProjectForm(instance=p)

    return render(request, 'update_project.html', {'form': form, 'project': p})


@login_required
def delete_project(request, pk):
    p = get_object_or_404(Project, pk=pk)
    if request.user != p.author:
        return HttpResponseForbidden("Faqat muallif o'chira oladi.")

    if request.method == 'POST':
        p.delete()
        messages.warning(request, "Loyiha o'chirildi.")
        return redirect('profile', username=request.user.username)
    return render(request, 'delete.html', {'project': p})


def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)

    # Muzlatilgan loyihani tekshirish
    if project.is_frozen and request.user != project.author and not request.user.is_superuser:
        messages.error(request, "Ushbu loyiha muzlatilgan.")
        return redirect('home')

    # Ko'rishlar sonini oshirish (F() obyekti poygasi holatini oldini oladi)
    Project.objects.filter(pk=pk).update(views=F('views') + 1)
    project.refresh_from_db()

    # Izoh qoldirish
    if request.method == 'POST' and request.user.is_authenticated:
        form = CommentForm(request.POST)
        if form.is_valid():
            c = form.save(commit=False)
            c.user = request.user
            c.project = project
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

    # Xarid qilinganligini tekshirish
    has_access = False
    if project.price == 0:
        has_access = True
    elif request.user.is_authenticated:
        if request.user == project.author or project.buyers.filter(id=request.user.id).exists():
            has_access = True

    is_synced = False
    if request.user.is_authenticated:
        is_synced = Sync.objects.filter(follower=request.user.profile, following=project.author.profile).exists()

    return render(request, 'project_detail.html', {
        'project': project,
        'form': CommentForm(),
        'code_preview': code_preview,
        'live_preview': is_html_file,
        'has_bought': has_access,
        'is_synced': is_synced
    })


@xframe_options_exempt
def live_project_view(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not project.source_code:
        return HttpResponse("Kod yo'q", content_type="text/plain")
    try:
        project.source_code.open('r')
        content = project.source_code.read()
        if isinstance(content, bytes):
            content = content.decode('utf-8', errors='ignore')
        project.source_code.close()
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
            liked = False
        else:
            p.likes.add(request.user)
            liked = True
            if p.author != request.user:
                notify.send(request.user, recipient=p.author, verb='like bosdi', target=p)
        return JsonResponse({'total_likes': p.likes.count(), 'is_liked': liked})
    return JsonResponse({'error': 'POST required'}, status=400)


@login_required
def save_project(request, pk):
    if request.method == 'POST':
        p = get_object_or_404(Project, pk=pk)
        if request.user in p.saved_by.all():
            p.saved_by.remove(request.user)
            saved = False
        else:
            p.saved_by.add(request.user)
            saved = True
        return JsonResponse({'is_saved': saved})
    return JsonResponse({'error': 'POST required'}, status=400)


@login_required
def toggle_sync(request, username):
    if request.method == 'POST':
        target_user = get_object_or_404(User, username=username)
        my_profile = request.user.profile
        target_profile = target_user.profile

        if my_profile == target_profile:
            return JsonResponse({'error': 'Self'}, status=400)

        obj = Sync.objects.filter(follower=my_profile, following=target_profile)
        if obj.exists():
            obj.delete()
            is_synced = False
        else:
            Sync.objects.create(follower=my_profile, following=target_profile)
            is_synced = True
            notify.send(request.user, recipient=target_user, verb='sinxronlashdi')

        return JsonResponse({
            'is_synced': is_synced,
            'followers_count': target_profile.followers.count()
        })
    return JsonResponse({'error': 'POST required'}, status=400)


@login_required
@transaction.atomic  # <--- MUHIM: Tranzaksiya xavfsizligi
def buy_project(request, pk):
    project = get_object_or_404(Project, pk=pk)
    buyer_profile = request.user.profile

    if project.is_frozen:
        messages.error(request, "Bu loyiha muzlatilgan, sotib olib bo'lmaydi.")
        return redirect('home')

    if request.user == project.author or project.buyers.filter(id=request.user.id).exists():
        return redirect('project_detail', pk=pk)

    if buyer_profile.balance >= project.price:
        # Pulni yechish
        buyer_profile.balance -= project.price
        buyer_profile.save()

        # Muallifga pul o'tkazish
        author_profile = project.author.profile
        author_profile.balance += project.price
        author_profile.save()

        # Xaridni rasmiylashtirish
        project.buyers.add(request.user)
        Transaction.objects.create(
            user=request.user,
            project=project,
            amount=project.price,
            status=Transaction.COMPLETED
        )

        notify.send(request.user, recipient=project.author, verb='sotib oldi', target=project)
        messages.success(request, f"'{project.title}' muvaffaqiyatli sotib olindi!")
    else:
        messages.error(request, "Hisobingizda mablag' yetarli emas.")
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
        superuser = User.objects.filter(is_superuser=True).first()
        if superuser:
            notify.send(superuser, recipient=p.author, verb='Loyiha Bloklandi (Juda ko\'p shikoyat)', target=p)
        messages.error(request, "Loyiha vaqtincha bloklandi.")
    else:
        messages.warning(request, "Shikoyat yuborildi. Rahmat!")

    return redirect('home')


# ==========================================
# 5. TOOLS & WALLET & PROFIL
# ==========================================
def online_compiler(request):
    result = ""
    if request.method == 'POST':
        source_code = request.POST.get('code', '')
        language = request.POST.get('language', 'python')

        # Piston API (EMKC)
        try:
            payload = {
                "language": language,
                "version": "*",
                "files": [{"content": source_code}]
            }
            response = requests.post("https://emkc.org/api/v2/piston/execute", json=payload, timeout=10)
            data = response.json()
            result = data.get('run', {}).get('stdout', '') or data.get('run', {}).get('stderr', '')
        except Exception as e:
            result = f"Xatolik yuz berdi: {str(e)}"

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'result': result})

    languages = [('python', 'Python'), ('javascript', 'Node.js'), ('cpp', 'C++'), ('java', 'Java')]
    return render(request, 'compiler.html', {'result': result, 'languages': languages})


def cpp_test(request):
    # Bu shunchaki compilerga yo'naltiradi, lekin alohida view sifatida so'ralgan
    return online_compiler(request)


@login_required
def add_funds(request):
    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount'))
            receipt = request.FILES.get('receipt')
            Deposit.objects.create(
                user=request.user,
                amount=amount,
                receipt=receipt,
                status=Deposit.PENDING
            )
            messages.success(request, "Chek yuborildi. Admin tasdiqlashini kuting.")
            return redirect('profile', username=request.user.username)
        except:
            messages.error(request, "Xato ma'lumot kiritildi.")

    return render(request, 'add_funds.html')


@login_required
def withdraw_money(request):
    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount'))
            card = request.POST.get('card_number')

            if amount > request.user.profile.balance:
                messages.error(request, "Balansda yetarli mablag' yo'q.")
            else:
                Withdrawal.objects.create(
                    user=request.user,
                    amount=amount,
                    card_number=card,
                    status=Withdrawal.PENDING
                )
                messages.success(request, "Pul yechish so'rovi yuborildi.")
                return redirect('profile', username=request.user.username)
        except:
            messages.error(request, "Xato ma'lumot.")

    return render(request, 'withdraw.html')


def profile(request, username=None):
    if username:
        target_user = get_object_or_404(User, username=username)
        is_owner = (request.user == target_user)
    else:
        if not request.user.is_authenticated:
            return redirect('login')
        target_user = request.user
        is_owner = True

    if request.method == 'POST' and is_owner:
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Profil yangilandi!')
            return redirect('profile', username=request.user.username)
    else:
        u_form = UserUpdateForm(instance=target_user)
        p_form = ProfileUpdateForm(instance=target_user.profile)

    user_projects = Project.objects.filter(author=target_user).order_by('-created_at')

    is_synced = False
    if request.user.is_authenticated and not is_owner:
        is_synced = Sync.objects.filter(follower=request.user.profile, following=target_user.profile).exists()

    return render(request, 'profile.html', {
        'target_user': target_user,
        'u_form': u_form,
        'p_form': p_form,
        'projects': user_projects,
        'is_owner': is_owner,
        'is_synced': is_synced
    })


@login_required
def community_chat(request):
    # Oxirgi 50 ta xabarni olish
    msgs = CommunityMessage.objects.all().order_by('-created_at')[:50]

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' and request.method == 'POST':
        txt = request.POST.get('body')
        if txt:
            CommunityMessage.objects.create(user=request.user, body=txt)

        # Yangi xabarlar ro'yxatini qaytarish
        return JsonResponse({
            'html': render_to_string('chat_messages_partial.html',
                                     {'chat_messages': reversed(msgs), 'request': request})
        })

    return render(request, 'community_chat.html', {'chat_messages': reversed(msgs)})


@login_required
def my_notifications(request):
    request.user.notifications.mark_all_as_read()
    return render(request, 'notifications.html', {'notifications': request.user.notifications.all()})


@login_required
def syncing_projects(request):
    # Obuna bo'lgan odamlarning ID lari
    following_profiles = request.user.profile.following.all()
    author_ids = [sync.following.user.id for sync in following_profiles]

    feed_projects = Project.objects.filter(author__id__in=author_ids).order_by('-created_at')
    return render(request, 'syncing.html', {'projects': feed_projects})


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
    return render(request, 'home.html', {'projects': Project.objects.filter(is_frozen=False).order_by('-views')[:20]})


def help_page(request):
    return render(request, 'help.html')


def announcements(request):
    # Oldingi suhbatda news.html yaratgan edik
    return render(request, 'news.html')


def portfolio_page(request):
    return render(request, 'index.html')


def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Ro'yxatdan o'tdingiz! Endi kiring.")
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'signup.html', {'form': form})


@login_required
def contact_page(request):
    if request.method == 'POST':
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        Contact.objects.create(user=request.user, subject=subject, message=message)
        messages.success(request, "Xabaringiz yuborildi.")
        return redirect('contact')
    return render(request, 'contact.html')


# ==========================================
# 6. FLUTTER API (DRF) VIEWS - TO'G'IRLANGAN
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
        # Token yaratish yoki borini olish
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
    permission_classes = [permissions.AllowAny]  # Hamma ko'ra olsin


# 4. LOYIHA YARATISH (Create)
class ProjectCreateAPI(generics.CreateAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)  # Rasmlarni qabul qilish uchun

    def perform_create(self, serializer):
        project = serializer.save(author=self.request.user)

        # Mobil ilovadan kelgan qo'shimcha rasmlarni saqlash
        images = self.request.FILES.getlist('more_images')
        for img in images:
            ProjectImage.objects.create(project=project, image=img)


# 5. BITTA LOYIHA (Detail)
class ProjectDetailAPI(generics.RetrieveAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


# 6. LOYIHANI O'ZGARTIRISH/O'CHIRISH (Update/Delete)
class ProjectUpdateDeleteAPI(generics.RetrieveUpdateDestroyAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Foydalanuvchi faqat o'z loyihasini o'chira oladi
        return Project.objects.filter(author=self.request.user)