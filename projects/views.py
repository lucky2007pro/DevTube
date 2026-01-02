import subprocess
import os
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
# ProjectImage ni import qilish esdan chiqmasin!
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


# 3. LOYIHA TAFSILOTLARI
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    project.views += 1
    project.save()

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
                    'avatar_url': comment.user.profile.avatar.url,
                    'body': comment.body,
                    'created_at': "hozirgina"
                })

            return redirect('project_detail', pk=pk)
    else:
        comment_form = CommentForm()

    has_bought = False
    code_content = None

    if project.price == 0 or (request.user.is_authenticated and request.user == project.author):
        has_bought = True

    if project.source_code and has_bought:
        file_ext = os.path.splitext(project.source_code.name)[1].lower()
        if file_ext in ['.zip', '.rar', '.7z', '.tar', '.gz']:
            code_content = "Bu arxiv fayl. Uni pastdagi tugma orqali yuklab olishingiz mumkin."
        else:
            try:
                code_content = "Faylni yuklab olib ko'rishingiz mumkin."
            except Exception:
                code_content = "Faylni o'qish imkonsiz."
    elif project.source_code:
        code_content = "# Kodni yuklab olish uchun loyihani sotib oling."

    context = {
        'project': project,
        'form': comment_form,
        'code_content': code_content,
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


# 9. SOTIB OLISH (MOCK)
@login_required
def buy_project(request, pk):
    project = get_object_or_404(Project, pk=pk)
    project.buyers.add(request.user)
    messages.success(request, f"{project.title} loyihasi sotib olindi!")
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


# 13. C++ INTEGRATSIYASI (YANGILANDI: AJAX va Dinamik Kompilyatsiya)
def cpp_test(request):
    result = ""
    code = ""
    input_data = ""

    if request.method == 'POST':
        code = request.POST.get('code', '')
        input_data = request.POST.get('input', '')

        # Fayl yo'lini aniqlash (Project root papkasida main.cpp va main.exe yaratiladi)
        file_path = os.path.join(settings.BASE_DIR, 'main.cpp')

        # Windows yoki Linux uchun output fayl nomi
        if os.name == 'nt':
            output_exe = os.path.join(settings.BASE_DIR, 'main.exe')
            run_cmd = [output_exe]
        else:
            output_exe = os.path.join(settings.BASE_DIR, 'main')
            run_cmd = [output_exe]

        # 1. C++ faylni yozish
        with open(file_path, 'w') as f:
            f.write(code)

        # 2. Kompilyatsiya qilish (g++)
        # Diqqat: Serverda (Render/Heroku/Local) g++ o'rnatilgan bo'lishi shart!
        compile_process = subprocess.run(['g++', file_path, '-o', output_exe], capture_output=True, text=True)

        if compile_process.returncode == 0:
            # 3. Ishga tushirish (Input berish bilan)
            try:
                # Linuxda ruxsat berish (agar kerak bo'lsa)
                if os.name != 'nt':
                    subprocess.run(['chmod', '+x', output_exe])

                run_process = subprocess.run(
                    run_cmd,
                    input=input_data,
                    capture_output=True,
                    text=True,
                    timeout=5  # 5 soniyadan oshsa to'xtatadi (Infinite loop himoyasi)
                )
                result = run_process.stdout
                if run_process.stderr:
                    result += "\nXatoliklar:\n" + run_process.stderr
            except subprocess.TimeoutExpired:
                result = "Xatolik: Dastur ishlash vaqti tugadi (Cheksiz tsikl?)"
            except Exception as e:
                result = f"Xatolik: {e}"
        else:
            result = "Kompilyatsiya xatosi:\n" + compile_process.stderr

        # AJAX so'rovlar uchun JSON qaytaramiz (Sahifa yangilanmasligi uchun)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'result': result})

    return render(request, 'cpp_test.html', {'code': code, 'input': input_data, 'result': result})