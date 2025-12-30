from django.contrib import admin
from .models import Project, Comment, Profile

# 1. Loyihalarni boshqarish
admin.site.register(Project)

# 2. Izohlarni boshqarish
admin.site.register(Comment)

# 3. Profillarni boshqarish (Foydalanuvchi rasmlari)
admin.site.register(Profile)