import os
import requests
import threading  # <--- MUHIM: Orqa fon jarayonlari uchun
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.clickjacking import xframe_options_exempt
from django.contrib import messages
from django.db.models import Q, F
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from notifications.signals import notify

# --- XAVFSIZLIK TIZIMI IMPORTLARI ---
from .security import scan_with_gemini, scan_with_virustotal

# --- FLUTTER API IMPORTLARI ---
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.parsers import MultiPartParser, FormParser
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
        # Cloudinary yoki S3 dan o'qish uchun url dan foydalanamiz
        # Agar fayl juda katta bo'lsa, hammasini o'qimaymiz (server qotmasligi uchun)
        if hasattr(project.source_code, 'url'):
            # Faqat sarlavha qismini qaytaramiz (Prevyu)
            return "// Kodni yuklab olish yoki to'liq ko'rish uchun loyihani oching."

        project.source_code.open('r')
        content = project.source_code.read(1000)
        text = content.decode('utf-8', errors='ignore') if isinstance(content, bytes) else content
        project.source_code.close()
        return "\n".join(text.splitlines()[:15]) + "\n..."
    except Exception:
        return "// Kodni o'qib bo'lmadi."


# --- XAVFSIZLIK TEKSHIRUVI (ORQA FONDA) ---
def run_security_scan(project_id):
    """
    Bu funksiya orqa fonda ishlaydi.
    Agar xavf aniqlansa, loyihani AVTOMATIK MUZLATADI (yashiradi).
    """
    try:
        project = Project.objects.get(id=project_id)
        if not project.source_code:
            return

        # Cloudinary URL
        file_url = project.source_code.url
        file_name = project.source_code.name

        # 1. Gemini Tekshiruvi
        ai_result = "Tahlil qilinmadi"
        try:
            # Faylni internetdan o'qib olamiz (timeout 10 soniya)
            response = requests.get(file_url, timeout=10)
            if response.status_code == 200:
                code_content = response.content.decode('utf-8', errors='ignore')
                ai_result = scan_with_gemini(code_content)
        except Exception as e:
            ai_result = f"O'qish xatosi: {e}"

        # 2. VirusTotal Tekshiruvi
        vt_link, vt_status = scan_with_virustotal(file_url, file_name)

        # 3. Natijani Saqlash
        project.ai_analysis = ai_result
        project.virustotal_link = vt_link
        project.is_scanned = True

        # --- MUHIM O'ZGARISH: AVTO-BLOKLASH ---
        # Agar Gemini "DANGER" desa YOKI VirusTotaldan yomon xabar kelsa
        if "DANGER" in str(ai_result) or (vt_status and "malicious" in str(vt_status)):
            project.security_status = 'danger'
            project.is_frozen = True  # <--- ZARARLI FAYLNI YASHIRAMIZ!
            print(f"DIQQAT! Loyiha {project_id} virus sababli bloklandi!")

        elif "SAFE" in str(ai_result):
            project.security_status = 'safe'
            # Agar oldin bloklangan bo'lsa va qayta tekshiruvda toza chiqsa, ochamiz
            if project.is_frozen and project.reports_count < 10:
                project.is_frozen = False

        else:
            project.security_status = 'warning'

        project.save()
        print(f"Project {project_id} scanned successfully!")

    except Exception as e:
        print(f"Scan Error: {e}")


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

            # --- XAVFSIZLIK: SCANNI FONDA ISHGA TUSHIRISH ---
            # Sayt qotib qolmasligi uchun Thread ishlatamiz
            if p.source_code:
                thread = threading.Thread(target=run_security_scan, args=(p.id,))
                thread.start()
                messages.success(request, f"'{p.title}' yuklandi! Xavfsizlik tekshiruvi boshlandi... 🛡️")
            else:
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
            p = form.save()
            # Agar yangi kod yuklansa, qayta tekshirish kerak
            if 'source_code' in request.FILES:
                p.is_scanned = False
                p.security_status = 'pending'
                p.save()
                thread = threading.Thread(target=run_security_scan, args=(p.id,))
                thread.start()
                messages.info(request, "Yangi kod tekshirilmoqda...")

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

    # Ko'rishlar sonini oshirish
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
    # URL borligini tekshirish (Cloudinary uchun)
    is_html_file = False
    if project.source_code and hasattr(project.source_code, 'name'):
        is_html_file = project.source_code.name.lower().endswith('.html')

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
    """
    Faylni Cloudinarydan o'qib, brauzerga HTML sifatida qaytarish
    """
    project = get_object_or_404(Project, pk=pk)
    if not project.source_code:
        return HttpResponse("Kod yo'q", content_type="text/plain")
    try:
        # Cloudinary URL orqali o'qish
        response = requests.get(project.source_code.url)
        if response.status_code == 200:
            content = response.content.decode('utf-8', errors='ignore')
            return HttpResponse(content, content_type="text/html")
        return HttpResponse("Faylni yuklab bo'lmadi", content_type="text/plain")
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
@transaction.atomic
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
    msgs = CommunityMessage.objects.all().order_by('-created_at')[:50]

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' and request.method == 'POST':
        txt = request.POST.get('body')
        if txt:
            CommunityMessage.objects.create(user=request.user, body=txt)

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
# 6. FLUTTER API (DRF) VIEWS
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


# 3. LOYIHALAR RO'YXATI
class ProjectListAPI(generics.ListAPIView):
    queryset = Project.objects.filter(is_frozen=False).order_by('-created_at')
    serializer_class = ProjectSerializer
    permission_classes = [permissions.AllowAny]


# 4. LOYIHA YARATISH
class ProjectCreateAPI(generics.CreateAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def perform_create(self, serializer):
        project = serializer.save(author=self.request.user)

        # Mobil ilovadan kelgan qo'shimcha rasmlarni saqlash
        images = self.request.FILES.getlist('more_images')
        for img in images:
            ProjectImage.objects.create(project=project, image=img)

        # API orqali ham scan qilish
        if project.source_code:
            thread = threading.Thread(target=run_security_scan, args=(project.id,))
            thread.start()


# 5. BITTA LOYIHA
class ProjectDetailAPI(generics.RetrieveAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


# 6. LOYIHANI O'ZGARTIRISH/O'CHIRISH
class ProjectUpdateDeleteAPI(generics.RetrieveUpdateDestroyAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(author=self.request.user)