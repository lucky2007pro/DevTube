import subprocess
import os
from django.conf import settings
from django.http import JsonResponse  # <--- YANGI QO'SHILDI (AJAX UCHUN)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Project, Comment, Profile
from .forms import ProjectForm, CommentForm, UserRegisterForm, UserUpdateForm, ProfileUpdateForm


# 1. BOSH SAHIFA (Qidiruv va Kategoriyalar bilan)
def home_page(request):
    q = request.GET.get('q') if request.GET.get('q') != None else ''
    category = request.GET.get('category')

    # Qidiruv logikasi
    projects = Project.objects.filter(
        Q(category__icontains=q) |
        Q(title__icontains=q) |
        Q(description__icontains=q)
    )

    # Kategoriya bo'yicha filter
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
            return redirect('home')

    return render(request, 'create_project.html', {'form': form})


# 3. LOYIHA TAFSILOTLARI (Ko'rish, Izoh, Sotib olish tekshiruvi)
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)

    # Ko'rishlar sonini oshirish
    project.views += 1
    project.save()

    # Izoh yozish
    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.user = request.user
            comment.project = project
            comment.save()
            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.user = request.user
                comment.project = project
                comment.save()

                # --- SHU YERDAN BOSHLAB QO'SHASIZ ---
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'username': comment.user.username,
                        'avatar_url': comment.user.profile.avatar.url,
                        'body': comment.body,
                        'created_at': "hozirgina"
                    })
                # --- SHU YERGACHA ---

                return redirect('project_detail', pk=pk)
            return redirect('project_detail', pk=pk)
    else:
        comment_form = CommentForm()

    # Kodni ko'rsatish (Tekin yoki sotib olingan yoki muallif o'zi bo'lsa)
    has_bought = False
    code_content = None
    is_preview = True

    if project.price == 0 or (request.user.is_authenticated and (request.user == project.author)):
        has_bought = True

    if has_bought and project.source_code:
        try:
            with project.source_code.open('r') as f:
                code_content = f.read()
            is_preview = False
        except:
            code_content = "Kod faylini o'qib bo'lmadi."
    elif project.source_code:
        # Agar sotib olmagan bo'lsa, kodni yashiramiz yoki qismini ko'rsatamiz
        code_content = "# Kodni ko'rish uchun loyihani sotib oling."

    context = {
        'project': project,
        'form': comment_form,
        'code_content': code_content,
        'has_bought': has_bought,
        'is_preview': is_preview
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


# 5. PROFIL VA SOZLAMALAR (RASM YANGILASH SHU YERDA)
@login_required
def profile(request):
    if request.method == 'POST':
        # MUHIM: request.FILES rasmni yuklash uchun shart!
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

    # Foydalanuvchining o'z loyihalari
    projects = Project.objects.filter(author=request.user).order_by('-created_at')

    context = {
        'u_form': u_form,
        'p_form': p_form,
        'projects': projects
    }
    return render(request, 'profile.html', context)


# 6. LOYIHANI O'CHIRISH
@login_required
def delete_project(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.user == project.author:
        if request.method == 'POST':
            project.delete()
            return redirect('profile')
        return render(request, 'delete.html', {'project': project})
    return redirect('home')


# 7. LOYIHANI TAHRIRLASH
@login_required
def update_project(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.user != project.author:
        return redirect('home')

    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES, instance=project)
        if form.is_valid():
            form.save()
            return redirect('project_detail', pk=pk)
    else:
        form = ProjectForm(instance=project)

    return render(request, 'update_project.html', {'form': form})


# 8. LIKE BOSISH (AJAX VERSION - YANGILANDI)
@login_required
def like_project(request, pk):
    if request.method == 'POST':
        project = get_object_or_404(Project, pk=pk)

        # Like bor-yo'qligini tekshirish
        if request.user in project.likes.all():
            project.likes.remove(request.user)
            is_liked = False
        else:
            project.likes.add(request.user)
            is_liked = True

        # Sahifani yangilash o'rniga JSON javob qaytaramiz
        return JsonResponse({
            'total_likes': project.likes.count(),
            'is_liked': is_liked
        })

    # Agar kimdir to'g'ridan-to'g'ri URL ga kirmoqchi bo'lsa
    return JsonResponse({'error': 'Faqat POST so\'rov qabul qilinadi'}, status=400)


# 9. SOTIB OLISH (MOCK)
@login_required
def buy_project(request, pk):
    project = get_object_or_404(Project, pk=pk)
    messages.success(request, f"{project.title} loyihasi sotib olindi (demo)!")
    return redirect('project_detail', pk=pk)


# 10. TRENDLAR
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


# 13. C++ INTEGRATSIYASI (main.exe ni ishlatish)
def cpp_test(request):
    result = "Hali hisoblanmadi..."

    if request.GET.get('number'):
        number = request.GET.get('number')

        # main.exe manzili: BASE_DIR/cpp_module/main.exe
        exe_path = os.path.join(settings.BASE_DIR, 'cpp_module', 'main.exe')

        try:
            # C++ dasturini (exe) ishga tushiramiz
            process = subprocess.run([exe_path, number], capture_output=True, text=True)

            if process.stdout:
                result = process.stdout
            else:
                result = f"Xatolik yoki bo'sh javob: {process.stderr}"
        except FileNotFoundError:
            result = "Xatolik: main.exe topilmadi!"
        except Exception as e:
            result = f"Dasturni ishga tushirib bo'lmadi: {e}"

    return render(request, 'cpp_test.html', {'result': result})