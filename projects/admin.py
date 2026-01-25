from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from django.contrib.auth.models import Group
from django.db.models import F

# Modellar importi
from .models import (
    Profile, Project, ProjectImage, Comment, Sync,
    CommunityMessage, Contact, Transaction, Withdrawal, Deposit
)

# =========================================================
# 🎨 1. ADMIN PANEL DIZAYNI
# =========================================================
admin.site.site_header = "DevTube Boshqaruv Paneli"
admin.site.site_title = "DevTube Admin"
admin.site.index_title = "Statistika va Boshqaruv"

if admin.site.is_registered(Group):
    admin.site.unregister(Group)


# =========================================================
# 👤 2. FOYDALANUVCHILAR (PROFIL)
# =========================================================
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('get_avatar', 'user', 'get_balance_styled', 'is_verified', 'bio_short')
    list_display_links = ('user', 'get_avatar')
    list_editable = ('is_verified',)  # To'g'ridan-to'g'ri admin panelda o'zgartirish
    search_fields = ('user__username', 'user__email')
    list_filter = ('is_verified',)
    list_per_page = 20

    def get_avatar(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover; border: 2px solid #6366f1;" />',
                obj.avatar.url)
        return format_html('<span style="font-size: 20px;">👤</span>')

    get_avatar.short_description = "Rasm"

    def get_balance_styled(self, obj):
        return format_html('<span style="color: #10b981; font-weight: bold;">${}</span>', obj.balance)

    get_balance_styled.short_description = "Balans"

    def bio_short(self, obj):
        return obj.bio[:50] + "..." if obj.bio else "-"

    bio_short.short_description = "Haqida"

    actions = ['reset_balance', 'make_verified']

    def reset_balance(self, request, queryset):
        queryset.update(balance=0)
        self.message_user(request, "Tanlangan foydalanuvchilar balansi nolga tushirildi.", messages.WARNING)

    reset_balance.short_description = "🗑 Balansni 0 qilish"

    def make_verified(self, request, queryset):
        queryset.update(is_verified=True)
        self.message_user(request, "Tanlangan foydalanuvchilarga 'Verified' belgisi berildi.", messages.SUCCESS)

    make_verified.short_description = "💎 'Verified' maqomini berish"


# =========================================================
# 🎬 3. LOYIHALAR (PROJECTS)
# =========================================================
class ProjectImageInline(admin.TabularInline):
    model = ProjectImage
    extra = 1


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    inlines = [ProjectImageInline]
    list_display = ('get_thumbnail', 'title', 'author', 'get_price_tag', 'get_security_badge', 'is_frozen', 'views')
    list_filter = ('category', 'security_status', 'is_frozen', 'created_at')
    search_fields = ('title', 'author__username', 'slug')
    list_editable = ('is_frozen',)
    prepopulated_fields = {"slug": ("title",)}
    list_per_page = 15

    def get_thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 80px; height: 45px; border-radius: 6px; object-fit: cover;" />',
                obj.image.url)
        return "🎬"

    get_thumbnail.short_description = "Muqova"

    def get_security_badge(self, obj):
        colors = {'safe': '#10b981', 'warning': '#f59e0b', 'danger': '#ef4444', 'pending': '#6b7280'}
        return format_html(
            '<span style="color: white; background: {}; padding: 2px 8px; border-radius: 8px; font-size: 10px; font-weight: bold;">{}</span>',
            colors.get(obj.security_status, 'gray'), obj.get_security_status_display())

    get_security_badge.short_description = "Xavfsizlik"

    def get_price_tag(self, obj):
        if obj.price == 0:
            return format_html('<span style="color: #10b981; font-weight: bold;">FREE</span>')
        return format_html('<span style="font-weight: bold;">${}</span>', obj.price)

    get_price_tag.short_description = "Narx"

    actions = ['freeze_projects', 'unfreeze_projects']

    def freeze_projects(self, request, queryset):
        queryset.update(is_frozen=True)
        self.message_user(request, "Loyihalar muzlatildi (yashirildi).", messages.ERROR)

    freeze_projects.short_description = "❄️ Loyihalarni muzlatish"


# =========================================================
# 💰 4. MOLIYA (DEPOSIT & WITHDRAWAL)
# =========================================================
@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = ('get_status_icon', 'user', 'amount', 'get_receipt_preview', 'created_at')
    list_filter = ('status',)
    actions = ['approve_deposit', 'reject_deposit']

    def get_status_icon(self, obj):
        icons = {'pending': '⏳ Pending', 'approved': '✅ Approved', 'rejected': '❌ Rejected'}
        colors = {'pending': '#f59e0b', 'approved': '#10b981', 'rejected': '#ef4444'}
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', colors.get(obj.status),
                           icons.get(obj.status))

    get_status_icon.short_description = "Holat"

    def get_receipt_preview(self, obj):
        if obj.receipt:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="height: 40px; border-radius: 4px; border: 1px solid #ddd;" /></a>',
                obj.receipt.url, obj.receipt.url)
        return "📄 Chek yo'q"

    def approve_deposit(self, request, queryset):
        for d in queryset.filter(status='pending'):
            profile = d.user.profile
            profile.balance += d.amount
            profile.save()
            d.status = 'approved'
            d.save()
        self.message_user(request, "To'lovlar tasdiqlandi va balansga qo'shildi.", messages.SUCCESS)


@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ('get_status_icon', 'user', 'amount', 'card_number', 'created_at')
    list_filter = ('status',)
    actions = ['mark_as_paid', 'reject_withdraw']

    def get_status_icon(self, obj):
        colors = {'pending': '#f59e0b', 'approved': '#10b981', 'rejected': '#ef4444'}
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', colors.get(obj.status),
                           obj.get_status_display())

    def mark_as_paid(self, request, queryset):
        queryset.update(status='approved')
        self.message_user(request, "To'lab berildi deb belgilandi.", messages.SUCCESS)

    def reject_withdraw(self, request, queryset):
        for w in queryset.filter(status='pending'):
            w.user.profile.balance += w.amount
            w.user.profile.save()
            w.status = 'rejected'
            w.save()
        self.message_user(request, "So'rovlar rad etildi va pul qaytarildi.", messages.ERROR)


# =========================================================
# 📦 5. IJTIMOIY (COMMENTS, SYNC, CHAT)
# =========================================================
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'project', 'body_short', 'created_at')
    search_fields = ('body', 'user__username', 'project__title')
    list_filter = ('created_at',)

    def body_short(self, obj):
        return obj.body[:40] + "..." if len(obj.body) > 40 else obj.body

    body_short.short_description = "Izoh matni"


@admin.register(Sync)
class SyncAdmin(admin.ModelAdmin):
    list_display = ('follower', 'following', 'created_at')
    search_fields = ('follower__user__username', 'following__user__username')


@admin.register(CommunityMessage)
class CommunityMessageAdmin(admin.ModelAdmin):
    list_display = ('user', 'body_short', 'created_at')
    list_per_page = 50

    def body_short(self, obj):
        return obj.body[:60] + "..." if len(obj.body) > 60 else obj.body


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'project', 'amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('subject', 'user', 'created_at')