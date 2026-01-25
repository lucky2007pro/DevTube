import json
import threading
from decimal import Decimal
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
import requests
from django.db.models import Q, Max
from .models import PrivateMessage # Importga qo'shing
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.postgres.search import TrigramSimilarity
from django.db import transaction
from django.db.models import Avg
from django.db.models import F
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

from .forms import (
    ProjectForm, UserRegisterForm, UserUpdateForm,
    ProfileUpdateForm, ReviewForm  # <--- Barcha formalar bitta joyda
)
from .models import (
    Project, ProjectImage, Sync, CommunityMessage,
    Contact, Transaction, Deposit, Withdrawal,
    Comment  # <--- Review va Comment modellari qo'shildi
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
# views.py ichidagi home_page funksiyasini yangilang

def home_page(request):
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    price_filter = request.GET.get('price', '') # 'free', 'premium'
    sort = request.GET.get('sort', '-views') # 'newest', 'popular'

    projects = Project.objects.filter(is_frozen=False)

    # 1. Aqlli qidiruv (Sarlavha va Tavsif ichidan)
    if query:
        # Sarlavha va tavsifdagi o'xshashlikni aniqlaymiz
        projects = projects.annotate(
            similarity=TrigramSimilarity('title', query) +
                       TrigramSimilarity('description', query)
        ).filter(similarity__gt=0.1).order_by('-similarity')  # 0.1 - sezgirlik darajasi
    else:
        # Agar qidiruv bo'lmasa, odatdagidek saralash
        sort = request.GET.get('sort', '-views')
        projects = projects.order_by(sort)

    # 2. Kategoriya filtri
    if category:
        projects = projects.filter(category=category)

    # 3. Narx filtri
    if price_filter == 'free':
        projects = projects.filter(price=0)
    elif price_filter == 'premium':
        projects = projects.filter(price__gt=0)

    # 4. Saralash
    if sort == 'newest':
        projects = projects.order_by('-created_at')
    else:
        projects = projects.order_by('-views') # Default: Ommaboplar

    return render(request, 'home.html', {
        'projects': projects,
        'categories': Project.CATEGORY_CHOICES,
        'search_query': query,
        'current_category': category,
        'current_price': price_filter,
        'current_sort': sort
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

# projects/views.py ning eng tepasiga qo'shing:


def project_detail(request, slug):
    project = get_object_or_404(Project, slug=slug)

    # 1. Ko'rishlar sonini oshirish
    Project.objects.filter(slug=slug).update(views=F('views') + 1)
    project.refresh_from_db()

    # 2. AJAX CHAT UCHUN LOGIKA (Pastdagi izohlar)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' and request.method == 'POST':
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Avval tizimga kiring'}, status=403)

        body = request.POST.get('body')
        if body:
            # Comment modeliga yozamiz
            comment = Comment.objects.create(project=project, user=request.user, body=body)
            return JsonResponse({
                'username': comment.user.username,
                'avatar_url': comment.user.profile.avatar.url if comment.user.profile.avatar else None,
                'body': comment.body,
                'created_at': 'Hozirgina'
            })
        return JsonResponse({'error': 'Bo\'sh xabar yozmang'}, status=400)

    # 3. KODNI O'QISH
    code_content = "// Kodni o'qib bo'lmadi."
    if project.source_code:
        try:
            if hasattr(project.source_code, 'url'):
                import requests
                response = requests.get(project.source_code.url, timeout=5)
                if response.status_code == 200:
                    code_content = response.content.decode('utf-8', errors='ignore')
            else:
                with project.source_code.open('r') as f:
                    code_content = f.read()
        except:
            pass

    # 4. REYTING TIZIMI MA'LUMOTLARI
    reviews = project.reviews.all().order_by('-created_at')
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    avg_rating = round(avg_rating, 1)

    # 5. BAHOLASH MUMKINMI?
    # 5. BAHOLASH MUMKINMI? (MANTIQ YANGILANDI)
    can_review = False
    user_review = None

    if request.user.is_authenticated:
        # A) Foydalanuvchi loyiha egasi EMASLIGINI tekshiramiz
        if request.user != project.author:

            # B) Oldin baho bermaganligini tekshiramiz
            already_reviewed = project.reviews.filter(user=request.user).exists()

            # C) Bepulmi yoki Sotib olganmi?
            # Narx 0 ga teng yoki umuman belgilanmagan (None) bo'lsa - BEPUL deb hisoblaymiz
            is_free = (project.price is None) or (project.price == 0)

            # Xaridorlar ro'yxatida bormi?
            is_buyer = project.buyers.filter(id=request.user.id).exists()

            # XULOSA: Agar (Bepul yoki Sotib olgan) bo'lsa VA (Baho bermagan) bo'lsa
            if (is_free or is_buyer) and not already_reviewed:
                can_review = True

            # Agar oldin baho bergan bo'lsa, o'z bahosini chiqarib beramiz
            if already_reviewed:
                user_review = project.reviews.filter(user=request.user).first()

    # 6. REYTINGNI SAQLASH (POST)
    review_form = ReviewForm()
    if request.method == 'POST' and 'rating' in request.POST:  # Rating kelganini tekshiramiz
        if can_review:
            review_form = ReviewForm(request.POST)
            if review_form.is_valid():
                review = review_form.save(commit=False)
                review.project = project
                review.user = request.user
                review.save()
                messages.success(request, "Bahoyingiz qabul qilindi! Rahmat.")
                return redirect('project_detail', slug=slug)

    # Context
    context = {
        'project': project,
        'code_content': code_content,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'can_review': can_review,
        'user_review': user_review,
        'form': review_form,  # Reyting formasi
        'has_bought': (project.price == 0 or (
                    request.user.is_authenticated and project.buyers.filter(id=request.user.id).exists())),
        'live_preview': project.source_code.name.lower().endswith('.html') if project.source_code else False,
        'is_synced': request.user.is_authenticated and Sync.objects.filter(follower=request.user.profile,
                                                                           following=project.author.profile).exists() if request.user.is_authenticated else False
    }

    return render(request, 'project_detail.html', context)


@xframe_options_exempt
def live_project_view(request, slug):  # <--- pk emas, slug bo'lishi shart!
    project = get_object_or_404(Project, slug=slug)  # <--- slug orqali qidiramiz

    if not project.source_code:
        return HttpResponse("Kod yo'q", content_type="text/plain")

    try:
        response = requests.get(project.source_code.url)
        if response.status_code == 200:
            content = response.content.decode('utf-8', errors='ignore')
            res = HttpResponse(content, content_type="text/html")
            # Brauzer bloklamasligi uchun xavfsizlik sarlavhalarini qo'shamiz
            res["X-Frame-Options"] = "ALLOWALL"
            return res
        return HttpResponse("Fayl topilmadi", content_type="text/plain")
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
    # 1. Loyihani olish
    project = get_object_or_404(Project, pk=pk)
    buyer_profile = request.user.profile

    # 2. Tekshiruvlar
    if project.is_frozen:
        messages.error(request, "Bu loyiha muzlatilgan, sotib olib bo'lmaydi.")
        return redirect('home')

    if request.user == project.author or project.buyers.filter(id=request.user.id).exists():
        return redirect('project_detail', slug=project.slug)

    # 3. Pulni yechish va muzlatish
    if buyer_profile.balance >= project.price:
        # A) Xaridordan pulni yechamiz
        buyer_profile.balance -= project.price
        buyer_profile.save()

        # B) Sotuvchining MUZLATILGAN balansiga qo'shamiz
        author_profile = project.author.profile
        author_profile.frozen_balance += project.price  # <--- Asosiy balance emas!
        author_profile.save()

        # C) Xaridorni qo'shish
        project.buyers.add(request.user)

        # D) Tranzaksiya yaratish (Status: HOLD)
        Transaction.objects.create(
            user=request.user,
            project=project,
            amount=project.price,
            status=Transaction.HOLD  # <--- Muzlatilgan status
        )

        # E) Telegram Xabar (Sotuvchiga)
        if author_profile.telegram_id:
            msg = (
                f"❄️ <b>Yangi savdo (Muzlatilgan)!</b>\n\n"
                f"Loyiha: <b>{project.title}</b>\n"
                f"Summa: <b>${project.price}</b> (Hold)\n"
                f"Xaridor: {request.user.username}\n\n"
                f"<i>Pul 3 kundan keyin yoki xaridor tasdiqlasa balansga o'tadi.</i>"
            )
            send_telegram_message(author_profile.telegram_id, msg)

        # F) Sayt bildirishnomasi
        notify.send(request.user, recipient=project.author, verb='sotib oldi (puli muzlatildi)', target=project)

        messages.success(request, f"'{project.title}' sotib olindi! Pul xavfsizlik uchun vaqtincha muzlatildi.")
    else:
        messages.error(request, "Hisobingizda mablag' yetarli emas.")
        return redirect('add_funds')

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
            # 1. Summani to'g'rilab olish
            amount_str = request.POST.get('amount', '').replace(',', '.')
            amount = Decimal(amount_str)

            # 2. Fayl borligini tekshirish
            receipt = request.FILES.get('receipt')
            if not receipt:
                messages.error(request, "Chek rasmi yuklanmadi!")
                return redirect('add_funds')

            # 3. Bazaga yozish (TUZATILDI)
            Deposit.objects.create(
                user=request.user,
                amount=amount,
                receipt=receipt,
                status='pending'  # <--- Deposit.PENDING o'rniga 'pending' yozdik
            )
            messages.success(request, "Chek qabul qilindi! Admin tasdiqlashini kuting.")
            return redirect('profile', username=request.user.username)

        except Exception as e:
            print(f"Xatolik: {e}")
            messages.error(request, "Xatolik yuz berdi. Iltimos qayta urinib ko'ring.")

    return render(request, 'add_funds.html')


# views.py ichiga qo'shing

@login_required
def withdraw_money(request):
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount', 0))
        card_number = request.POST.get('card_number', '')

        if amount < 5:  # Minimal yechish miqdori $5
            messages.error(request, "Minimal yechish miqdori $5")
        elif amount > request.user.profile.balance:
            messages.error(request, "Balansingizda mablag' yetarli emas.")
        elif len(card_number) < 16:
            messages.error(request, "Karta raqami noto'g'ri.")
        else:
            # So'rov yaratish
            Withdrawal.objects.create(
                user=request.user,
                amount=amount,
                card_number=card_number
            )
            # Balansni vaqtincha muzlatish yoki ayirish
            request.user.profile.balance -= amount
            request.user.profile.save()

            messages.success(request, "Pul yechish so'rovi yuborildi. Admin tasdiqlashini kuting.")
            return redirect('profile')

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
    my_purchases = []
    my_sales = []

    if is_owner:
        # Men sotib olganlarim
        my_purchases = Transaction.objects.filter(user=target_user).order_by('-created_at')

        # Men sotganlarim (Project orqali topamiz)
        my_sales = Transaction.objects.filter(project__author=target_user).order_by('-created_at')
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
        'user_url': user_absolute_url, # Tashqi foydalanuvchilar uchun link
        'my_purchases': my_purchases,
        'my_sales': my_sales
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


# projects/views.py faylining eng oxiriga qo'shing

def fix_database_slugs(request):
    import random
    import string

    # Faqat admin kirishi uchun xavfsizlik
    if not request.user.is_superuser:
        return HttpResponseForbidden("Bu sahifaga faqat admin kira oladi.")

    # Slug'i bo'sh bo'lgan hamma loyihalarni topamiz
    projects = Project.objects.filter(slug__isnull=True) | Project.objects.filter(slug='')
    count = 0

    for p in projects:
        # Tasodifiy 11 talik YouTube-style ID yaratamiz
        new_slug = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(11))

        # Unikallikni tekshiramiz
        while Project.objects.filter(slug=new_slug).exists():
            new_slug = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(11))

        p.slug = new_slug
        p.save()
        count += 1

    return HttpResponse(f"Muvaffaqiyatli! {count} ta loyiha linki (slug) bazada tuzatildi.")


# projects/views.py ning eng oxiriga qo'shing:


@login_required
def admin_dashboard(request):
    # 1. UMUMIY STATISTIKA
    total_users = User.objects.count()
    total_projects = Project.objects.count()
    total_revenue = Transaction.objects.filter(status='completed').aggregate(Sum('amount'))['amount__sum'] or 0

    # 2. ONLINE FOYDALANUVCHILAR
    time_threshold = timezone.now() - timedelta(minutes=15)
    online_users = User.objects.filter(profile__last_activity__gte=time_threshold).count()

    # 3. TOP XARIDORLAR
    # 'transactions' - bu Transaction modelidagi user related_name
    top_spenders = User.objects.annotate(
        total_spent=Sum('transactions__amount', filter=Q(transactions__status='completed'))
    ).filter(total_spent__gt=0).order_by('-total_spent')[:10]

    # 4. ENG FAOL SOTUVCHILAR (Tuzatildi ✅)
    # User -> Project ('project') -> Transaction ('transaction_set')
    top_sellers = User.objects.annotate(
        total_sales=Count(
            'project__transaction_set',
            filter=Q(project__transaction_set__status='completed')
        )
    ).filter(total_sales__gt=0).order_by('-total_sales')[:10]

    context = {
        'total_users': total_users,
        'total_projects': total_projects,
        'total_revenue': total_revenue,
        'online_users': online_users,
        'top_spenders': top_spenders,
        'top_sellers': top_sellers,
    }
    return render(request, 'stats.html', context)


# projects/views.py

from django.db.models import Q, Max
from .models import PrivateMessage  # Importga qo'shing


@login_required
def inbox(request):
    # Men bilan yozishgan barcha odamlarni topamiz (takrorlanmasin)
    users = User.objects.filter(
        Q(sent_messages__receiver=request.user) |
        Q(received_messages__sender=request.user)
    ).distinct().exclude(id=request.user.id)

    # Har bir user bilan oxirgi xabarni topish (Sorting uchun)
    chats = []
    for user in users:
        last_msg = PrivateMessage.objects.filter(
            (Q(sender=request.user) & Q(receiver=user)) |
            (Q(sender=user) & Q(receiver=request.user))
        ).last()

        # O'qilmagan xabarlar soni (Men uchun)
        unread_count = PrivateMessage.objects.filter(sender=user, receiver=request.user, is_read=False).count()

        chats.append({
            'user': user,
            'last_msg': last_msg,
            'unread': unread_count
        })

    # Eng yangi xabar yozganlarni tepaga chiqaramiz
    chats.sort(key=lambda x: x['last_msg'].created_at if x['last_msg'] else timezone.now(), reverse=True)

    return render(request, 'inbox.html', {'chats': chats})


@login_required
def direct_chat(request, username):
    target_user = get_object_or_404(User, username=username)

    # Xabar yuborish (POST)
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        body = request.POST.get('body')
        if body:
            msg = PrivateMessage.objects.create(
                sender=request.user,
                receiver=target_user,
                body=body
            )
            # Javob qaytaramiz (Frontendga qo'shish uchun)
            return JsonResponse({
                'status': 'ok',
                'sender': request.user.username,
                'avatar': request.user.profile.avatar.url if request.user.profile.avatar else None,
                'body': msg.body,
                'time': 'Hozirgina'
            })

    # O'qildi deb belgilash (Agar men ochsam)
    PrivateMessage.objects.filter(sender=target_user, receiver=request.user, is_read=False).update(is_read=True)

    # Yozishmalar tarixi
    messages = PrivateMessage.objects.filter(
        (Q(sender=request.user) & Q(receiver=target_user)) |
        (Q(sender=target_user) & Q(receiver=request.user))
    )

    return render(request, 'direct_chat.html', {
        'target_user': target_user,
        'messages': messages
    })


# projects/views.py ichiga qo'shing

@login_required
@transaction.atomic
def confirm_purchase(request, pk):
    # 1. Tranzaksiyani topamiz (Faqat xaridor o'zi tasdiqlay oladi va status HOLD bo'lishi kerak)
    trx = get_object_or_404(Transaction, pk=pk, user=request.user, status=Transaction.HOLD)

    # 2. Statusni o'zgartiramiz
    trx.status = Transaction.COMPLETED
    trx.save()

    # 3. Sotuvchining muzlatilgan pulini asosiy balansga o'tkazamiz
    seller_profile = trx.project.author.profile

    # Xavfsizlik uchun tekshiramiz: Muzlatilgan balansda yetarli pul bormi?
    if seller_profile.frozen_balance >= trx.amount:
        seller_profile.frozen_balance -= trx.amount  # Muzlatilgandan olamiz
        seller_profile.balance += trx.amount  # Asosiyga qo'shamiz
        seller_profile.save()

        # Sotuvchiga xabar
        if seller_profile.telegram_id:
            send_telegram_message(
                seller_profile.telegram_id,
                f"✅ <b>Pul yechildi!</b>\n\nXaridor tasdiqladi. <b>${trx.amount}</b> asosiy balansingizga o'tdi."
            )

        messages.success(request, "Xarid tasdiqlandi! Pul sotuvchiga o'tkazib berildi.")
    else:
        # Agar qandaydir xatolik bo'lib, muzlatilgan balans yetmasa
        messages.error(request, "Tizim xatoligi: Sotuvchi balansida muammo bor. Adminga xabar bering.")

    return redirect('profile')  # Yoki transaction history


@login_required
def raise_dispute(request, pk):
    # Faqat 'HOLD' (Muzlatilgan) statusdagi tranzaksiyaga shikoyat qilish mumkin
    trx = get_object_or_404(Transaction, pk=pk, user=request.user, status=Transaction.HOLD)

    if request.method == 'POST':
        # 1. Statusni 'DISPUTED' (Nizoli) ga o'zgartiramiz
        trx.status = Transaction.DISPUTED
        trx.save()

        # 2. Adminga xabar beramiz
        superuser = User.objects.filter(is_superuser=True).first()
        if superuser:
            notify.send(request.user, recipient=superuser, verb='Nizo ochdi', target=trx.project)

        messages.warning(request,
                         "Shikoyat qabul qilindi! Adminlar tez orada vaziyatni o'rganib chiqadi. Pul sotuvchiga o'tkazilmaydi.")
        return redirect('profile')

    return render(request, 'raise_dispute.html', {'trx': trx})


@login_required
def resolve_dispute(request, pk, decision):
    # Faqat Admin kira oladi
    if not request.user.is_superuser:
        return redirect('home')

    trx = get_object_or_404(Transaction, pk=pk, status=Transaction.DISPUTED)
    seller_profile = trx.project.author.profile
    buyer_profile = trx.user.profile

    if decision == 'refund':
        # XARIDOR HAQ: Pulni qaytarib beramiz
        if seller_profile.frozen_balance >= trx.amount:
            seller_profile.frozen_balance -= trx.amount  # Muzlatilgandan olib tashlaymiz
            seller_profile.save()

            buyer_profile.balance += trx.amount  # Xaridorga qaytaramiz
            buyer_profile.save()

            trx.status = Transaction.CANCELED  # Bekor qilindi
            trx.save()
            messages.success(request, f"Pul ${trx.amount} xaridorga qaytarildi.")

    elif decision == 'release':
        # SOTUVCHI HAQ: Pulni sotuvchiga beramiz
        if seller_profile.frozen_balance >= trx.amount:
            seller_profile.frozen_balance -= trx.amount
            seller_profile.balance += trx.amount  # Asosiy balansga o'tdi
            seller_profile.save()

            trx.status = Transaction.COMPLETED
            trx.save()
            messages.success(request, f"Nizo yopildi. Pul sotuvchiga berildi.")

    return redirect('admin_stats')  # Yoki admin panel