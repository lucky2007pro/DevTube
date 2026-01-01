from django import forms
from django.contrib.auth.models import User
from .models import Project, Profile, Comment


# 1. LOYIHA YUKLASH FORMASI
class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        # Hamma kerakli maydonlarni kiritamiz
        fields = ['title', 'description', 'image', 'video_file', 'source_code', 'price', 'category', 'youtube_link']

        # HTML dagi inputlarga chiroyli dizayn (Bootstrap) berish
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Loyiha nomi'}),
            'description': forms.Textarea(
                attrs={'class': 'form-control', 'placeholder': 'Loyiha haqida batafsil...', 'rows': 4}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Narxi (0 = Tekin)'}),
            'youtube_link': forms.URLInput(
                attrs={'class': 'form-control', 'placeholder': 'https://youtube.com/watch?v=...'}),
            'video_file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'source_code': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


# 2. IZOH YOZISH FORMASI
class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['body']
        widgets = {
            'body': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Izoh qoldiring...'})
        }


# 3. RO'YXATDAN O'TISH FORMASI
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


# 4. USER MA'LUMOTLARINI YANGILASH
class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }


# 5. PROFIL (RASM) YANGILASH
class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['bio', 'avatar']
        widgets = {
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'O\'zingiz haqida...'}),
            'avatar': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }