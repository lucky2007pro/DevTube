import json
import threading
from decimal import Decimal

import requests
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q, F
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from notifications.signals import notify
# --- FLUTTER API IMPORTLARI ---
from rest_framework import generics, permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .forms import ProjectForm, CommentForm, UserRegisterForm, UserUpdateForm, ProfileUpdateForm
from .models import (
    Project, ProjectImage, Sync, CommunityMessage,
    Contact, Transaction, Deposit, Withdrawal
)
# --- XAVFSIZLIK TIZIMI IMPORTLARI ---
from .security import scan_with_gemini, scan_with_virustotal
from .serializers import ProjectSerializer, RegisterSerializer, ProfileSerializer
from .utils import generate_telegram_link  # Import qilishni unutmang
from .utils import send_telegram_message
from .utils import verify_telegram_token


# ==========================================
# 1. YORDAMCHI FUNKSIYALAR & ORQA FON (THREAD)
# ==========================================

def get_code_snippet(project):
    """Manba kodi oynasi uchun qisqa preview"""
    if not project.source_code:
        return "// Kod yuklanmagan."
    try:
        if hasattr(project.source_code, 'url'):
            return "// Kodni yuklab olish yoki to'liq ko'rish uchun loyihani oching."

        project.source_code.open('r')
        content = project.source_code.read(1000)
        text = content.decode('utf-8', errors='ignore') if isinstance(content, bytes) else content
        project.source_code.close()
        return "\n".join(text.splitlines()[:15]) + "\n..."
    except Exception:
        return "// Kodni o'qib bo'lmadi."


def run_security_scan(project_id):
    """
    Bu funksiya orqa fonda ishlaydi.
    1. Faylni Cloudinarydan o'qiydi.
    2. Gemini va VirusTotaldan o'tkazadi.
    3. Agar xavf aniqlansa, loyihani AVTOMATIK MUZLATADI.
    4. Agar xato chiqsa, sayt qotib qolmasligi uchun statusni yangilaydi.
    """
    try:
        project = Project.objects.get(id=project_id)
        if not project.source_code:
            return

        # Cloudinary URL
        file_url = project.source_code.url
        file_name = project.source_code.name
        print(f"DEBUG: Scan boshlandi ID: {project_id}, URL: {file_url}")

        # --- 1. GEMINI TEKSHIRUVI ---
        ai_result = "Tahlil qilinmadi"
        try:
            # Faylni internetdan o'qib olamiz (timeout 20 soniya - katta fayllar uchun)
            response = requests.get(file_url, timeout=20)
            if response.status_code == 200:
                try:
                    code_content = response.content.decode('utf-8', errors='ignore')
                    ai_result = scan_with_gemini(code_content)
                except:
                    ai_result = "Fayl matn formatida emas (Binary), faqat VirusTotal tekshiradi."
            else:
                ai_result = f"Faylni yuklab bo'lmadi. Status: {response.status_code}"
        except Exception as e:
            ai_result = f"AI/Request Xatosi: {e}"

        # --- 2. VIRUSTOTAL TEKSHIRUVI ---
        vt_link, vt_status = scan_with_virustotal(file_url, file_name)

        # --- 3. NATIJALARNI SAQLASH ---
        project.ai_analysis = ai_result
        project.virustotal_link = vt_link
        project.is_scanned = True  # Loading to'xtaydi

        # --- 4. HUKM CHIQARISH (AVTO-BLOKLASH) ---
        is_dangerous_ai = "DANGER" in str(ai_result)
        is_dangerous_vt = vt_status and "malicious" in str(vt_status).lower()

        if is_dangerous_ai or is_dangerous_vt:
            project.security_status = 'danger'
            project.is_frozen = True  # <--- ZARARLI FAYLNI YASHIRAMIZ!
            print(f"DIQQAT! Loyiha {project_id} xavfli deb topildi va bloklandi!")

        elif "SAFE" in str(ai_result):
            project.security_status = 'safe'
            # Agar oldin avtomatik bloklangan bo'lsa va endi toza chiqsa, ochamiz
            if project.is_frozen and project.reports_count < 10:
                project.is_frozen = False

        else:
            project.security_status = 'warning'

        project.save()
        print(f"Loyiha {project_id} tekshiruvi yakunlandi: {project.security_status}")

    except Exception as e:
        # AGAR XATO CHIQSA HAM FOYDALANUVCHINI KUTTIRMASLIK KERAK
        print(f"CRITICAL SCAN ERROR: {e}")
        try:
            p = Project.objects.get(id=project_id)
            p.is_scanned = True
            p.security_status = 'warning'
            p.ai_analysis = f"Tizim xatoligi yuz berdi: {str(e)}. Iltimos, keyinroq qayta urinib ko'ring."
            p.save()
        except:
            pass


# ==========================================
# 2. ASOSIY SAHIFA
# ==========================================
def home_page(request):
    query = request.GET.get('q')
    category = request.GET.get('category')
    price_filter = request.GET.get('price') # 'free', 'premium' yoki narx oralig'i

    projects = Project.objects.filter(is_frozen=False)

    # 1. Aqlli qidiruv
    if query:
        projects = projects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(author__username__icontains=query)  # Muallif nomi bo'yicha ham qidiradi
        ).distinct()

    # 2. Kategoriya bo'yicha filtr
    if category:
        projects = projects.filter(category=category)

    # 3. Narx bo'yicha filtr
    if price_filter == 'free':
        projects = projects.filter(price=0)
    elif price_filter == 'premium':
        projects = projects.filter(price__gt=0)

    return render(request, 'home.html', {
        'projects': projects.order_by('-views'),
        'categories': Project.CATEGORY_CHOICES,
        'search_query': query
    })


# ==========================================
# 3. LOYIHA AMALLARI (WEB)
# ==========================================
@login_required
@transaction.atomic
def create_project(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # 1. Loyihani saqlash
                p = form.save(commit=False)
                p.author = request.user
                p.is_scanned = False
                p.security_status = 'pending'
                p.save()

                # 2. Rasmlarni saqlash
                for img in request.FILES.getlist('more_images'):
                    ProjectImage.objects.create(project=p, image=img)

                # 3. XAVFSIZLIK: SCANNI TRANZAKSIYA TUGAGACH ISHGA TUSHIRISH (TUZATILDI)
                if p.source_code:
                    # Lambda funksiya orqali commit bo'lgandan keyin threadni ishga tushiramiz
                    transaction.on_commit(
                        lambda: threading.Thread(target=run_security_scan, args=(p.id,), daemon=True).start()
                    )
                    messages.success(request, f"'{p.title}' yuklandi! Xavfsizlik tekshiruvi orqa fonda boshlandi... 🛡️")
                else:
                    messages.success(request, f"'{p.title}' muvaffaqiyatli yuklandi!")

                return redirect('home')
            except Exception as e:
                messages.error(request, f"Xatolik yuz berdi: {e}")
        else:
            messages.error(request, "Formada xatolik bor.")
    else:
        form = ProjectForm()
    return render(request, 'create_project.html', {'form': form})


@login_required
@transaction.atomic  # Bu yerga ham atomic qo'shish tavsiya etiladi
def update_project(request, pk):
    p = get_object_or_404(Project, pk=pk)
    if request.user != p.author:
        messages.error(request, "Bu loyihani tahrirlash huquqiga ega emassiz!")
        return redirect('home')

    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES, instance=p)
        if form.is_valid():
            p = form.save(commit=False)

            # Agar yangi kod yuklansa, qayta tekshirish kerak
            if 'source_code' in request.FILES:
                p.is_scanned = False
                p.security_status = 'pending'
                p.save()

                # TUZATILDI: on_commit ishlatildi
                transaction.on_commit(
                    lambda: threading.Thread(target=run_security_scan, args=(p.id,), daemon=True).start()
                )
                messages.info(request, "Yangi kod qayta tekshirilmoqda...")
            else:
                p.save()
                messages.success(request, "Loyiha yangilandi!")

            return redirect('project_detail', slug=p.slug)
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


# views.py ichida:

def project_detail(request, slug):
    project = get_object_or_404(Project, slug=slug)

    # Muzlatilgan loyihani tekshirish
    if project.is_frozen and request.user != project.author and not request.user.is_superuser:
        messages.error(request, "Ushbu loyiha bloklangan.")
        return redirect('home')

    # Ko'rishlar sonini oshirish
    Project.objects.filter(slug=slug).update(views=F('views') + 1)
    project.refresh_from_db()

    # --- KODNI O'QISH QISMI (YANGI) ---
    code_content = "// Kodni o'qib bo'lmadi."
    if project.source_code:
        try:
            # 1. Agar fayl URL bo'lsa (Cloudinary/S3/Render serverda)
            if hasattr(project.source_code, 'url'):
                import requests
                # Fayl matnini internetdan tortib olamiz
                response = requests.get(project.source_code.url)
                if response.status_code == 200:
                    code_content = response.content.decode('utf-8', errors='ignore')
                else:
                    code_content = "// Fayl serverda topilmadi."

            # 2. Agar lokal kompyuterda bo'lsa
            else:
                with project.source_code.open('r') as f:
                    code_content = f.read()
        except Exception as e:
            code_content = f"// Xatolik: {e}"
    else:
        code_content = "// Kod yuklanmagan."

    # HTML fayl ekanligini aniqlash (Live Preview uchun)
    is_html_file = False
    if project.source_code and hasattr(project.source_code, 'name'):
        is_html_file = project.source_code.name.lower().endswith('.html')

    # Sotib olganligini tekshirish
    has_access = False
    if project.price == 0:
        has_access = True
    elif request.user.is_authenticated:
        if request.user == project.author or project.buyers.filter(id=request.user.id).exists():
            has_access = True

    # Izoh qoldirish logikasi
    if request.method == 'POST' and request.user.is_authenticated:
        form = CommentForm(request.POST)
        if form.is_valid():
            c = form.save(commit=False)
            c.user = request.user
            c.project = project
            c.save()
            return redirect('project_detail', slug=slug)

    is_synced = False
    if request.user.is_authenticated:
        is_synced = Sync.objects.filter(follower=request.user.profile, following=project.author.profile).exists()

    return render(request, 'project_detail.html', {
        'project': project,
        'form': CommentForm(),

        # ⚠️ ENG MUHIMI: Kod matnini alohida yuboryapmiz
        'code_content': code_content,

        'live_preview': is_html_file,
        'has_bought': has_access,
        'is_synced': is_synced
    })


@xframe_options_exempt  # <iframe> ichida ochishga ruxsat
def live_project_view(request, slug):  # <--- 'pk' emas, 'slug' deb yozing
    project = get_object_or_404(Project, slug=slug)  # <--- 'pk' emas, 'slug'
    if not project.source_code:
        return HttpResponse("Kod yuklanmagan.", content_type="text/plain")

    try:
        # Fayl URL manzilini olamiz
        file_url = project.source_code.url
        response = requests.get(file_url, timeout=10)

        if response.status_code == 200:
            content = response.content.decode('utf-8', errors='ignore')
            # 🛡️ XAVFSIZLIK: Brauzerga Frame ichida ochishga ruxsat beramiz
            res = HttpResponse(content, content_type="text/html")
            res["X-Frame-Options"] = "ALLOWALL"
            res["Content-Security-Policy"] = "frame-ancestors *"
            return res

        return HttpResponse("Faylni yuklab bo'lmadi.", content_type="text/plain")
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
    # 1. Loyihani ID orqali bazadan olish
    project = get_object_or_404(Project, pk=pk)
    buyer_profile = request.user.profile

    # 2. Muzlatilgan loyihani tekshirish
    if project.is_frozen:
        messages.error(request, "Bu loyiha muzlatilgan, sotib olib bo'lmaydi.")
        return redirect('home')

    # 3. Oldin sotib olganligini yoki muallif ekanligini tekshirish
    if request.user == project.author or project.buyers.filter(id=request.user.id).exists():
        # MUHIM: pk=pk emas, slug=project.slug bo'lishi shart!
        return redirect('project_detail', slug=project.slug)

    # 4. Mablag'ni tekshirish va tranzaksiyani amalga oshirish
    if buyer_profile.balance >= project.price:
        # Xaridor hisobidan yechish
        buyer_profile.balance -= project.price
        buyer_profile.save()

        # Sotuvchi hisobiga tushirish
        author_profile = project.author.profile
        author_profile.balance += project.price
        author_profile.save()

        # Xaridorni ro'yxatga qo'shish
        project.buyers.add(request.user)

        # 5. Telegram orqali sotuvchiga bildirishnoma yuborish
        author_telegram_id = author_profile.telegram_id
        if author_telegram_id:
            msg = (
                f"🎉 <b>Tabriklaymiz!</b>\n\n"
                f"Sizning <b>{project.title}</b> loyihangiz sotildi!\n"
                f"💰 Summa: <b>${project.price}</b>\n"
                f"👤 Xaridor: {request.user.username}\n\n"
                f"<i>Balansingizni tekshirib ko'ring!</i>"
            )
            send_telegram_message(author_telegram_id, msg)

        # 6. Tranzaksiya tarixini yaratish
        Transaction.objects.create(
            user=request.user,
            project=project,
            amount=project.price,
            status=Transaction.COMPLETED  # Modeldagi statusga mos kelishini tekshiring
        )

        # 7. Sayt ichidagi bildirishnoma (Notification)
        notify.send(request.user, recipient=project.author, verb='loyihangizni sotib oldi', target=project)

        messages.success(request, f"'{project.title}' muvaffaqiyatli sotib olindi!")
    else:
        messages.error(request, "Hisobingizda mablag' yetarli emas.")
        return redirect('add_funds')

    # MUHIM: Eng oxirgi yo'naltirish ham slug orqali bo'lishi shart!
    return redirect('project_detail', slug=project.slug)


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
    # 1. Foydalanuvchini aniqlash
    if username:
        target_user = get_object_or_404(User, username=username)
        is_owner = (request.user == target_user)
    else:
        if not request.user.is_authenticated:
            return redirect('login')
        target_user = request.user
        is_owner = True

    # 2. ISHONCHLI SOTUVCHI (VERIFIED) LOGIKASI
    # Foydalanuvchining muvaffaqiyatli sotgan loyihalari sonini hisoblaymiz
    # Eslatma: Transaction modelida COMPLETED statusi 'completed' ekanligiga ishonch hosil qiling
    sold_count = Transaction.objects.filter(
        project__author=target_user,
        status='completed'
    ).count()

    # Avtomatik "Verified" maqomini berish
    if sold_count >= 5 and not target_user.profile.is_verified:
        target_user.profile.is_verified = True
        target_user.profile.save()

    # 3. Profilni tahrirlash (Faqat egasi uchun)
    if request.method == 'POST' and is_owner:
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Profil ma’lumotlari muvaffaqiyatli yangilandi!')
            return redirect('profile', username=request.user.username)
    else:
        u_form = UserUpdateForm(instance=target_user)
        p_form = ProfileUpdateForm(instance=target_user.profile)

    # 4. Foydalanuvchi loyihalari
    user_projects = Project.objects.filter(author=target_user).order_by('-created_at')

    # 5. Qo'shimcha ma'lumotlar (Sinxronizatsiya va Telegram)
    is_synced = False
    if request.user.is_authenticated and not is_owner:
        is_synced = Sync.objects.filter(
            follower=request.user.profile,
            following=target_user.profile
        ).exists()

    telegram_link = None
    if is_owner:
        telegram_link = generate_telegram_link(request.user)

    # 6. User Link (SEO va ulashish uchun shaxsiy havola)
    user_absolute_url = request.build_absolute_uri()

    return render(request, 'profile.html', {
        'target_user': target_user,
        'u_form': u_form,
        'p_form': p_form,
        'projects': user_projects,
        'is_owner': is_owner,
        'is_synced': is_synced,
        'telegram_link': telegram_link,
        'sold_count': sold_count,
        'user_url': user_absolute_url # Tashqi foydalanuvchilar uchun link
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


class ProjectListAPI(generics.ListAPIView):
    queryset = Project.objects.filter(is_frozen=False).order_by('-created_at')
    serializer_class = ProjectSerializer
    permission_classes = [permissions.AllowAny]


class ProjectCreateAPI(generics.CreateAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    # TUZATILDI: Tranzaksiya bilan ishlash uchun method override qilindi
    @transaction.atomic
    def perform_create(self, serializer):
        project = serializer.save(author=self.request.user)
        images = self.request.FILES.getlist('more_images')
        for img in images:
            ProjectImage.objects.create(project=project, image=img)

        if project.source_code:
            # TUZATILDI: on_commit ishlatildi
            transaction.on_commit(
                lambda: threading.Thread(target=run_security_scan, args=(project.id,), daemon=True).start()
            )

class ProjectDetailAPI(generics.RetrieveAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class ProjectUpdateDeleteAPI(generics.RetrieveUpdateDestroyAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(author=self.request.user)



@csrf_exempt  # Telegram CSRF token yubormaydi, shuning uchun o'chiramiz
def telegram_webhook(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            # Agar xabar bo'lsa
            if 'message' in data:
                chat_id = data['message']['chat']['id']
                text = data['message'].get('text', '')

                # Agar /start buyrug'i bo'lsa
                if text.startswith('/start'):
                    parts = text.split()

                    # Agar token ham bo'lsa (/start TOKEN)
                    if len(parts) > 1:
                        token = parts[1]
                        user_id = verify_telegram_token(token)

                        if user_id:
                            try:
                                user = User.objects.get(id=user_id)
                                # Telegram ID ni profilga saqlaymiz
                                user.profile.telegram_id = chat_id
                                user.profile.save()

                                send_telegram_message(chat_id,
                                                      f"✅ <b>Muvaffaqiyatli ulandi!</b>\nAssalomu alaykum, {user.username}!\nEndi bildirishnomalar shu yerga keladi.")
                            except User.DoesNotExist:
                                send_telegram_message(chat_id, "❌ Foydalanuvchi topilmadi.")
                        else:
                            send_telegram_message(chat_id,
                                                  "⚠️ Havola eskirgan yoki noto'g'ri. Saytdan qayta urinib ko'ring.")
                    else:
                        send_telegram_message(chat_id, "Bot ishlashi uchun saytdagi havola orqali kiring.")

        except Exception as e:
            print(f"Webhook xatosi: {e}")

        return HttpResponse('OK')
    return HttpResponse('Not a POST request')