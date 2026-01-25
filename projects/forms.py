from django import forms
from django.contrib.auth.models import User
# ProjectImage ni import qilishni unutmang!
from .models import Project, Profile, Comment, ProjectImage
from .models import Project, Review

# --- YANGI: BIR NECHTA RASM YUKLASH UCHUN YORDAMCHI KLASSLAR ---
class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


# ----------------------------------------------------------------

# 1. LOYIHA YUKLASH FORMASI
class ProjectForm(forms.ModelForm):
    # Qo'shimcha rasmlar maydoni (Gallery)
    more_images = MultipleFileField(
        label="Qo'shimcha Skrinshotlar",
        required=False,
        widget=MultipleFileInput(attrs={'class': 'form-control', 'multiple': True})
    )

    class Meta:
        model = Project
        fields = ['title', 'description', 'image', 'source_code', 'price', 'category', 'youtube_link']

        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Loyiha nomi'}),
            'description': forms.Textarea(
                attrs={'class': 'form-control', 'placeholder': 'Loyiha haqida batafsil...', 'rows': 4}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Narxi (0 = Tekin)'}),
            'youtube_link': forms.URLInput(
                attrs={'class': 'form-control', 'placeholder': 'https://youtube.com/watch?v=... (Majburiy)'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'source_code': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


# 2. QO'SHIMCHA RASMLAR FORMASI (Yangi qo'shildi)
class ProjectImageForm(forms.ModelForm):
    class Meta:
        model = ProjectImage
        fields = ['image']


# 3. IZOH YOZISH FORMASI
class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['body']
        widgets = {
            'body': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Izoh qoldiring...'})
        }


# 4. RO'YXATDAN O'TISH FORMASI
class UserRegisterForm(forms.ModelForm):
    email = forms.EmailField(required=True,
                             widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Parol'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Login'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


# 5. USER MA'LUMOTLARINI YANGILASH
class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }


# 6. PROFIL (RASM) YANGILASH
class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['bio', 'avatar']
        widgets = {
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'O\'zingiz haqida...'}),
            'avatar': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-select bg-dark text-white border-secondary'}),
            'comment': forms.Textarea(attrs={
                'class': 'form-control bg-dark text-white border-secondary',
                'rows': 3,
                'placeholder': 'Loyiha haqida fikringiz (ixtiyoriy)...'
            }),
        }