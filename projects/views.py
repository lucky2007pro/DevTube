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

    # 1. Izohlar qismi
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

    # 2. Sotib olish va Kodni ko'rish
    has_bought = project.price == 0 or (request.user.is_authenticated and
                                        (request.user == project.author or request.user in project.buyers.all()))

    code_preview, live_preview = get_code_preview(project)

    context = {
        'project': project,
        'form': CommentForm(),
        'code_preview': code_preview,
        'live_preview': live_preview,
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
    return render(request, 'signup.html', {'form': form})


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
@login_required
def update_project(request, pk):
    project = get_object_or_404(Project, pk=pk)

    # Faqat muallif tahrirlay oladi
    if request.user != project.author:
        messages.error(request, "Siz faqat o'z loyihangizni tahrirlashingiz mumkin.")
        return redirect('home')

    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES, instance=project)
        if form.is_valid():
            project = form.save()

            # Qo'shimcha rasmlarni yuklash
            images = request.FILES.getlist('more_images')
            for img in images:
                ProjectImage.objects.create(project=project, image=img)

            messages.success(request, "Loyiha muvaffaqiyatli yangilandi!")
            # project_detail sahifasiga loyiha pk-si bilan qaytamiz
            return redirect('project_detail', pk=project.pk)
    else:
        form = ProjectForm(instance=project)

    # project obyektini contextga qo'shish shart! (Rasmda aynan shu yetishmayotgan edi)
    return render(request, 'update_project.html', {'form': form, 'project': project})

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