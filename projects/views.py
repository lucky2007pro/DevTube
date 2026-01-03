import os
import subprocess
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q

# Modellar va Formalar
from .models import Project, Comment, ProjectImage
from .forms import ProjectForm, CommentForm, UserRegisterForm, UserUpdateForm, ProfileUpdateForm


# 1. BOSH SAHIFA
def home_page(request):
    q = request.GET.get('q') if request.GET.get('q') != None else ''
    category = request.GET.get('category')

    projects = Project.objects.filter(
        Q(category__icontains=q) |
        Q(title__icontains=q) |
        Q(description__icontains=q)
    )

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
    form = ProjectForm()
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

    return render(request, 'create_project.html', {'form': form})


# 3. LOYIHA TAFSILOTLARI (LIVE PREVIEW BILAN)
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)

    project.views += 1
    project.save()

    # --- IZOHLAR ---
    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.user = request.user
            comment.project = project
            comment.save()

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'username': comment.user.username,
                    'avatar_url': comment.user.profile.avatar.url if comment.user.profile.avatar else '',
                    'body': comment.body,
                    'created_at': "hozirgina"
                })

            return redirect('project_detail', pk=pk)
    else:
        comment_form = CommentForm()

    # --- SOTIB OLISH ---
    has_bought = False
    if project.price == 0:
        has_bought = True
    elif request.user.is_authenticated:
        if request.user == project.author or request.user in project.buyers.all():
            has_bought = True

    # --- KOD VA LIVE PREVIEW LOGIKASI ---
    code_preview = "// Kod mavjud emas."
    live_preview = None  # <--- YANGI O'ZGARUVCHI (HTML natijasi uchun)

    if project.source_code:
        try:
            ext = os.path.splitext(project.source_code.name)[1].lower()
            text_extensions = ['.css', '.js', '.py', '.php', '.txt', '.cpp', '.c', '.java', '.json']

            # 1. AGAR HTML BO'LSA -> JONLI NATIJA (IFRAME UCHUN)
            if ext == '.html':
                project.source_code.open('r')

                # To'liq o'qib olamiz (Iframe uchun)
                full_content = project.source_code.read()
                if isinstance(full_content, bytes):
                    live_preview = full_content.decode('utf-8', errors='ignore')
                else:
                    live_preview = full_content

                # Kursor boshiga qaytariladi (Preview uchun 15 qator olishga)
                project.source_code.seek(0)
                lines = []
                for _ in range(15):
                    line = project.source_code.readline()
                    if not line: break
                    if isinstance(line, bytes):
                        lines.append(line.decode('utf-8', errors='ignore'))
                    else:
                        lines.append(line)
                code_preview = "".join(lines)
                project.source_code.close()

            # 2. BOSHQA FAYLLAR -> FAQAT KOD
            elif ext in text_extensions:
                project.source_code.open('r')
                lines = []
                for _ in range(15):
                    line = project.source_code.readline()
                    if not line: break
                    if isinstance(line, bytes):
                        lines.append(line.decode('utf-8', errors='ignore'))
                    else:
                        lines.append(line)
                code_preview = "".join(lines)
                project.source_code.close()

            elif ext in ['.zip', '.rar', '.7z', '.tar', '.gz']:
                code_preview = "// Bu arxiv fayl (ZIP/RAR).\n// Kodni ko'rish uchun loyihani xarid qiling va yuklab oling."
            else:
                code_preview = "// Bu fayl formatini oldindan ko'rish imkonsiz."

        except Exception as e:
            code_preview = f"// Xatolik: {str(e)}"

    context = {
        'project': project,
        'form': comment_form,
        'code_preview': code_preview,
        'live_preview': live_preview,  # Shablonga yuboramiz
        'has_bought': has_bought,
    }
    return render(request, 'project_detail.html', context)


# 4. RO'YXATDAN O'TISH
def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Siz muvaffaqiyatli ro\'yxatdan o\'tdingiz. Endi kirishingiz mumkin.')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'register.html', {'form': form})


# 5. PROFIL
@login_required
def profile(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Profil muvaffaqiyatli yangilandi!')
            return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)

    projects = Project.objects.filter(author=request.user).order_by('-created_at')

    context = {
        'u_form': u_form,
        'p_form': p_form,
        'projects': projects
    }
    return render(request, 'profile.html', context)


# 6. O'CHIRISH
@login_required
def delete_project(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.user == project.author:
        if request.method == 'POST':
            project.delete()
            return redirect('profile')
        return render(request, 'delete.html', {'project': project})
    return redirect('home')


# 7. TAHRIRLASH
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

            messages.success(request, "Loyiha yangilandi!")
            return redirect('project_detail', pk=pk)
    else:
        form = ProjectForm(instance=project)

    return render(request, 'update_project.html', {'form': form})


# 8. LIKE (AJAX)
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


# 9. SOTIB OLISH
@login_required
def buy_project(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.user in project.buyers.all() or request.user == project.author:
        messages.info(request, "Siz bu loyihani allaqachon sotib olgansiz.")
    else:
        project.buyers.add(request.user)
        messages.success(request, f"{project.title} loyihasi muvaffaqiyatli sotib olindi!")

    return redirect('project_detail', pk=pk)


# 10. TRENDING
def trending(request):
    projects = Project.objects.all().order_by('-views')
    categories = Project.CATEGORY_CHOICES
    return render(request, 'home.html', {'projects': projects, 'categories': categories})


# 11. YOQQAN LOYIHALAR
@login_required
def liked_videos(request):
    projects = Project.objects.filter(likes=request.user)
    categories = Project.CATEGORY_CHOICES
    return render(request, 'home.html', {'projects': projects, 'categories': categories})


# 12. MENING LOYIHALARIM
@login_required
def my_videos(request):
    projects = Project.objects.filter(author=request.user)
    categories = Project.CATEGORY_CHOICES
    return render(request, 'home.html', {'projects': projects, 'categories': categories})


# 13. C++ INTEGRATSIYASI
def cpp_test(request):
    result = ""
    code = ""
    input_data = ""

    if request.method == 'POST':
        code = request.POST.get('code', '')
        input_data = request.POST.get('input', '')

        file_path = os.path.join(settings.BASE_DIR, 'main.cpp')

        if os.name == 'nt':
            output_exe = os.path.join(settings.BASE_DIR, 'main.exe')
        else:
            output_exe = os.path.join(settings.BASE_DIR, 'main')

        with open(file_path, 'w') as f:
            f.write(code)

        try:
            compile_process = subprocess.run(
                ['g++', file_path, '-o', output_exe],
                capture_output=True,
                text=True
            )

            if compile_process.returncode == 0:
                if os.name != 'nt':
                    subprocess.run(['chmod', '+x', output_exe])

                run_process = subprocess.run(
                    [output_exe],
                    input=input_data,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                result = run_process.stdout
                if run_process.stderr:
                    result += "\nXatoliklar:\n" + run_process.stderr
            else:
                result = "Kompilyatsiya xatosi:\n" + compile_process.stderr

        except FileNotFoundError:
            result = "Serverda G++ kompilyatori o'rnatilmagan."
        except subprocess.TimeoutExpired:
            result = "Dastur ishlash vaqti tugadi (Infinite Loop)."
        except Exception as e:
            result = f"Tizim xatoligi: {str(e)}"

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'result': result})

    return render(request, 'cpp_test.html', {'code': code, 'input': input_data, 'result': result})