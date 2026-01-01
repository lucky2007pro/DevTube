from django import forms
from django.contrib.auth.models import User
from .models import Project, Profile, Comment


# 1. LOYIHA YUKLASH FORMASI
class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['title', 'description', 'image', 'source_code', 'price', 'category', 'youtube_link']

# 2. IZOH YOZISH FORMASI
class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['body']


# 3. RO'YXATDAN O'TISH FORMASI (UserCreationForm o'rniga o'zimiznikini yozamiz)
class UserRegisterForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


# 4. USER MA'LUMOTLARINI YANGILASH
class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email']


# 5. PROFIL (RASM) YANGILASH
class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['bio', 'avatar']