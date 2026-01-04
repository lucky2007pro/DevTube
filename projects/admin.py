from django.contrib import admin
from .models import Project, Comment, Profile
from .models import Contact  # Contact ni import qilishni unutmang

# 1. Loyihalarni boshqarish
admin.site.register(Project)

# 2. Izohlarni boshqarish
admin.site.register(Comment)

# 3. Profillarni boshqarish (Foydalanuvchi rasmlari)
admin.site.register(Profile)

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('user', 'subject', 'created_at')
    search_fields = ('user__username', 'subject', 'message')
    list_filter = ('created_at',)