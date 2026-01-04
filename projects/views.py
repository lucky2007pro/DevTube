import os
import re
import requests  # <-- MUHIM: API ishlashi uchun
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.models import User
from django.template.loader import render_to_string

# Modellar va Formalar
from .models import Project, Comment, ProjectImage, Sync, Profile, CommunityMessage
from .forms import ProjectForm, CommentForm, UserRegisterForm, UserUpdateForm, ProfileUpdateForm


# 1. BOSH SAHIFA
def home_page(request):
    q = request.GET.get('q') if request.GET.get('q') != None else ''
    category = request.GET.get('category')

    projects = Project.objects.filter(
        Q(category__icontains=q) |
        Q(title__icontains=q) |
        Q(description__icontains=q)
    ).distinct()

    if category:
        projects = projects.filter(category=category)

    # Views bo'yicha saralash
    projects = projects.order_by('-views')

    categories = Project.CATEGORY_CHOICES
    context = {'projects': projects, 'categories': categories}
    return render(request, 'home.html', context)


# 2. LOYIHA YUKLASH
@login_required
def create_project(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES)
        if form.is_valid():
            project = form.save(commit=False)
            project.author = request.user
            project.save()

            images = request.FILES.getlist('more_images')
            for img in images:
                ProjectImage.objects.create(project=project, image=img)

            messages.success(request, "Loyiha muvaffaqiyatli yuklandi!")
            return redirect('home')
    else:
        form = ProjectForm()

    return render(request, 'create_project.html', {'form': form})


# 3. LOYIHA TAFSILOTLARI (LIVE PREVIEW BILAN)
def get_code_preview(project):
    """Fayl mazmunini o'qish uchun yordamchi funksiya"""
    if not project.source_code:
        return "// Kod mavjud emas.", None

    try:
        ext = os.path.splitext(project.source_code.name)[1].lower()
        with project.source_code.open('r') as f:
            content = f.read()
            full_text = content.decode('utf-8', errors='ignore') if isinstance(content, bytes) else content

            # Preview uchun 15 qator
            preview = "\n".join(full_text.splitlines()[:15])

            if ext == '.html':
                return preview, full_text  # Preview va Live natija
            elif ext in ['.css', '.js', '.py', '.cpp', '.json', '.txt']:
                return preview, None
            elif ext in ['.zip', '.rar']:
                return "// Bu arxiv fayl. Kodni ko'rish uchun yuklab oling.", None
    except Exception as e:
        return f"// Xatolik: {str(e)}", None
    return "// Bu fayl formatini ko'rib bo'lmaydi.", None


def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    Project.objects.filter(pk=pk).update(views=project.views + 1)

    # 1. Izohlar qismi (AJAX so'rovi bilan)
    if request.method == 'POST' and request.user.is_authenticated:
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user, comment.project = request.user, project
            comment.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'username': comment.user.username,
                    'avatar_url': comment.user.profile.avatar.url if comment.user.profile.avatar else '',
                    'body': comment.body,
                    'created_at': "hozirgina"
                })
            return redirect('project_detail', pk=pk)

    # 2. Sotib olish va Kodni ko'rish holati
    has_bought = project.price == 0 or (request.user.is_authenticated and
                                        (request.user == project.author or request.user in project.buyers.all()))

    code_preview, live_preview = get_code_preview(project)

    # 3. Sync holati
    is_synced = False
    if request.user.is_authenticated:
        is_synced = Sync.objects.filter(follower=request.user.profile, following=project.author.profile).exists()

    context = {
        'project': project,
        'form': CommentForm(),
        'code_preview': code_preview,
        'live_preview': live_preview,
        'has_bought': has_bought,
        'is_synced': is_synced,
    }
    return render(request, 'project_detail.html', context)


# 4. SYNC (SINXRONLANISH) - AJAX
@login_required
def toggle_sync(request, username):
    if request.method == 'POST':
        target_user = get_object_or_404(User, username=username)
        target_profile = target_user.profile
        my_profile = request.user.profile

        if my_profile == target_profile:
            return JsonResponse({'error': 'Ozingizga sinxron bo\'la olmaysiz'}, status=400)

        sync_query = Sync.objects.filter(follower=my_profile, following=target_profile)

        if sync_query.exists():
            sync_query.delete()
            is_synced = False
        else:
            Sync.objects.create(follower=my_profile, following=target_profile)
            is_synced = True

        return JsonResponse({
            'is_synced': is_synced,
            'followers_count': target_profile.followers.count()
        })
    return JsonResponse({'error': 'POST talab qilinadi'}, status=400)


# 5. RO'YXATDAN O'TISH
def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ro\'yxatdan o\'tdingiz. Kirishingiz mumkin.')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'signup.html', {'form': form})


# 6. PROFIL (O'ziniki va Boshqalarniki)
def profile(request, username=None):
    if username:
        # Boshqa dasturchining profilini ko'rish
        target_user = get_object_or_404(User, username=username)
        is_owner = (request.user == target_user)
    else:
        # O'z profilini ko'rish
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

    projects = Project.objects.filter(author=target_user).order_by('-created_at')

    # Sync holatini tekshirish
    is_synced = False
    if request.user.is_authenticated and not is_owner:
        is_synced = Sync.objects.filter(follower=request.user.profile, following=target_user.profile).exists()

    context = {
        'target_user': target_user,
        'u_form': u_form,
        'p_form': p_form,
        'projects': projects,
        'is_owner': is_owner,
        'is_synced': is_synced,
    }
    return render(request, 'profile.html', context)


# 7. LIKE (AJAX)
@login_required
def like_project(request, pk):
    if request.method == 'POST':
        project = get_object_or_404(Project, pk=pk)
        if request.user in project.likes.all():
            project.likes.remove(request.user)
            is_liked = False
        else:
            project.likes.add(request.user)
            is_liked = True

        return JsonResponse({
            'total_likes': project.likes.count(),
            'is_liked': is_liked
        })
    return JsonResponse({'error': 'POST required'}, status=400)


# 8. SOTIB OLISH
@login_required
def buy_project(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.user in project.buyers.all() or request.user == project.author:
        messages.info(request, "Sizda ruxsat bor.")
    else:
        # Hamyon tekshiruvi bu yerga qo'shilishi mumkin
        project.buyers.add(request.user)
        messages.success(request, f"{project.title} sotib olindi!")

    return redirect('project_detail', pk=pk)


# 9. TRENDING, LIKED, MY VIDEOS
def trending(request):
    projects = Project.objects.all().order_by('-views')
    categories = Project.CATEGORY_CHOICES
    return render(request, 'home.html', {'projects': projects, 'categories': categories})


@login_required
def liked_videos(request):
    projects = Project.objects.filter(likes=request.user)
    return render(request, 'home.html', {'projects': projects})


@login_required
def my_videos(request):
    projects = Project.objects.filter(author=request.user)
    return render(request, 'home.html', {'projects': projects})


# 10. TAHRIRLASH VA O'CHIRISH
@login_required
def update_project(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.user != project.author:
        return redirect('home')

    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES, instance=project)
        if form.is_valid():
            project = form.save()
            images = request.FILES.getlist('more_images')
            for img in images:
                ProjectImage.objects.create(project=project, image=img)
            messages.success(request, "Yangilandi!")
            return redirect('project_detail', pk=project.pk)
    else:
        form = ProjectForm(instance=project)
    return render(request, 'update_project.html', {'form': form, 'project': project})


@login_required
def delete_project(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.user == project.author:
        if request.method == 'POST':
            project.delete()
            return redirect('profile', username=request.user.username)
        return render(request, 'delete.html', {'project': project})
    return redirect('home')


# 11. UNIVERSAL ONLINE COMPILER (Piston API)
def online_compiler(request):
    result = ""
    code = ""
    input_data = ""
    language = "python"  # Default til

    # Piston API tillari xaritasi
    LANGUAGES = [
        ('html', 'HTML5 (Web)'),
        ('python', 'Python 3'),
        ('javascript', 'Node.js (JS)'),
        ('cpp', 'C++'),
        ('java', 'Java'),
        ('go', 'Go'),
        ('php', 'PHP'),
        ('csharp', 'C#'),
        ('ruby', 'Ruby'),
    ]

    if request.method == 'POST':
        code = request.POST.get('code', '')
        input_data = request.POST.get('input', '')
        language = request.POST.get('language', 'python')

        # API ga so'rov yuborish (Piston API)
        url = "https://emkc.org/api/v2/piston/execute"
        payload = {
            "language": language,
            "version": "*",
            "files": [{"content": code}],
            "stdin": input_data
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            data = response.json()

            if 'run' in data:
                output = data['run'].get('stdout', '')
                error = data['run'].get('stderr', '')
                result = output + "\n" + error
            else:
                result = "Xatolik: API javob bermadi."

        except Exception as e:
            result = f"Ulanish xatosi: {str(e)}"

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'result': result})

    context = {
        'code': code,
        'input': input_data,
        'result': result,
        'languages': LANGUAGES,
        'current_lang': language
    }
    return render(request, 'compiler.html', context)


# 14. SINXRONLARIM (SUBSCRIPTIONS)
@login_required
def syncing_projects(request):
    # Siz "Sync" qilgan (kuzatayotgan) profillarni olamiz
    my_syncs = request.user.profile.following.all().values_list('following__user', flat=True)

    # O'sha dasturchilar tomonidan yuklangan loyihalar
    projects = Project.objects.filter(author__id__in=my_syncs).order_by('-created_at')

    categories = Project.CATEGORY_CHOICES
    context = {
        'projects': projects,
        'categories': categories,
        'page_title': 'Sinxronlarim'
    }
    return render(request, 'syncing.html', context)


# 15. COMMUNITY CHAT (JONLI CHAT)
@login_required
def community_chat(request):
    # Oxirgi 50 ta xabarni olish
    messages = CommunityMessage.objects.all().order_by('-created_at')[:50]
    chat_messages = reversed(messages)  # Eskidan yangiga qarab chiqarish

    # AJAX so'rovlarini tekshirish (sahifa yangilanmasligi uchun)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        if request.method == 'POST':
            body = request.POST.get('body')
            if body:
                CommunityMessage.objects.create(user=request.user, body=body)

        # Yangi xabarlarni render qilib qaytarish
        html = render_to_string('chat_messages_partial.html', {'chat_messages': chat_messages, 'request': request})
        return JsonResponse({'html': html})

    return render(request, 'community_chat.html', {'chat_messages': chat_messages})


# 16. SAQLANGANLAR (BOOKMARK)
@login_required
def save_project(request, pk):
    if request.method == 'POST':
        project = get_object_or_404(Project, pk=pk)
        if request.user in project.saved_by.all():
            project.saved_by.remove(request.user)
            is_saved = False
        else:
            project.saved_by.add(request.user)
            is_saved = True

        return JsonResponse({'is_saved': is_saved})
    return JsonResponse({'error': 'POST required'}, status=400)


@login_required
def saved_projects(request):
    # Foydalanuvchi saqlagan barcha loyihalar
    projects = request.user.saved_projects.all().order_by('-created_at')
    context = {
        'projects': projects,
        'categories': Project.CATEGORY_CHOICES,
        'page_title': 'Saqlangan Loyihalar'
    }
    return render(request, 'home.html', context)