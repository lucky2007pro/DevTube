from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from django.contrib.auth.models import Group
from django.db import transaction  # <--- MUHIM: Moliya xavfsizligi uchun

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

# Guruhlar (Groups) kerak bo'lmasa o'chirib turamiz
if admin.site.is_registered(Group):
    admin.site.unregister(Group)


# =========================================================
# 👤 2. FOYDALANUVCHILAR (PROFIL)
# =========================================================
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    # 'user' ni oldindan yuklaymiz, baza qiynalmasligi uchun
    list_select_related = ('user',)

    list_display = ('get_avatar', 'user', 'get_balance_styled', 'is_verified', 'telegram_id')
    list_display_links = ('user', 'get_avatar')
    list_editable = ('is_verified',)
    search_fields = ('user__username', 'user__email', 'telegram_id')
    list_filter = ('is_verified', 'user__date_joined')
    list_per_page = 20

    def get_avatar(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover; border: 2px solid #6366f1;" />',
                obj.avatar.url
            )
        return format_html('<span style="font-size: 20px;">👤</span>')

    get_avatar.short_description = "Rasm"

    def get_balance_styled(self, obj):
        color = "#10b981" if obj.balance > 0 else "#6b7280"
        return format_html('<span style="color: {}; font-weight: bold;">${:.2f}</span>', color, obj.balance)

    get_balance_styled.short_description = "Balans"

    actions = ['reset_balance', 'make_verified']

    @admin.action(description="🗑 Balansni 0 qilish")
    def reset_balance(self, request, queryset):
        # Admin xatolik bilan bosib yubormasligi uchun
        count = queryset.update(balance=0)
        self.message_user(request, f"{count} ta foydalanuvchi balansi tozalandi.", messages.WARNING)

    @admin.action(description="💎 'Verified' maqomini berish")
    def make_verified(self, request, queryset):
        count = queryset.update(is_verified=True)
        self.message_user(request, f"{count} ta foydalanuvchi tasdiqlandi.", messages.SUCCESS)


# =========================================================
# 🎬 3. LOYIHALAR (PROJECTS)
# =========================================================
class ProjectImageInline(admin.TabularInline):
    model = ProjectImage
    extra = 1


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_select_related = ('author',)  # Avtor ma'lumotlarini tez yuklash
    inlines = [ProjectImageInline]

    list_display = ('get_thumbnail', 'title', 'author', 'get_price_tag', 'get_security_badge', 'is_frozen', 'views',
                    'created_at')
    list_filter = ('category', 'security_status', 'is_frozen', 'created_at')
    search_fields = ('title', 'author__username', 'description')
    list_editable = ('is_frozen',)
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ('views', 'likes', 'saved_by', 'buyers')  # Bularni admin qo'lda o'zgartirmasligi kerak
    list_per_page = 15

    def get_thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 80px; height: 45px; border-radius: 6px; object-fit: cover;" />',
                obj.image.url
            )
        return "🎬"

    get_thumbnail.short_description = "Muqova"

    def get_security_badge(self, obj):
        colors = {'safe': '#10b981', 'warning': '#f59e0b', 'danger': '#ef4444', 'pending': '#6b7280'}
        status_text = obj.get_security_status_display()
        return format_html(
            '<span style="color: white; background: {}; padding: 2px 8px; border-radius: 8px; font-size: 10px; font-weight: bold;">{}</span>',
            colors.get(obj.security_status, 'gray'), status_text
        )

    get_security_badge.short_description = "Xavfsizlik"

    def get_price_tag(self, obj):
        if obj.price == 0:
            return format_html('<span style="color: #10b981; font-weight: bold;">FREE</span>')
        return format_html('<span style="font-weight: bold;">${}</span>', obj.price)

    get_price_tag.short_description = "Narx"

    actions = ['freeze_projects', 'unfreeze_projects']

    @admin.action(description="❄️ Loyihalarni muzlatish")
    def freeze_projects(self, request, queryset):
        queryset.update(is_frozen=True)
        self.message_user(request, "Loyihalar muzlatildi.", messages.ERROR)

    @admin.action(description="🔥 Muzlatishdan chiqarish")
    def unfreeze_projects(self, request, queryset):
        queryset.update(is_frozen=False)
        self.message_user(request, "Loyihalar faollashtirildi.", messages.SUCCESS)


# =========================================================
# 💰 4. MOLIYA (TRANZAKSIYA XAVFSIZLIGI)
# =========================================================
@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_select_related = ('user',)
    list_display = ('get_status_icon', 'user', 'amount', 'get_receipt_preview', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username',)
    readonly_fields = ('created_at',)  # Sanani o'zgartirib bo'lmasin

    actions = ['approve_deposit', 'reject_deposit']

    def get_status_icon(self, obj):
        icons = {'pending': '⏳ Kutilmoqda', 'approved': '✅ Tasdiqlandi', 'rejected': '❌ Rad etildi'}
        colors = {'pending': '#f59e0b', 'approved': '#10b981', 'rejected': '#ef4444'}
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', colors.get(obj.status),
                           icons.get(obj.status))

    get_status_icon.short_description = "Holat"

    def get_receipt_preview(self, obj):
        if obj.receipt:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="height: 40px; border-radius: 4px; border: 1px solid #ddd;" /></a>',
                obj.receipt.url, obj.receipt.url
            )
        return "📄 Chek yo'q"

    get_receipt_preview.short_description = "Chek"

    @admin.action(description="✅ Tasdiqlash (Balansga qo'shish)")
    def approve_deposit(self, request, queryset):
        count = 0
        with transaction.atomic():  # <--- XAVFSIZLIK: Tranzaksiya butunlay bajariladi yoki umuman bajarilmaydi
            for deposit in queryset:
                if deposit.status == 'pending':
                    profile = deposit.user.profile
                    profile.balance += deposit.amount
                    profile.save()

                    deposit.status = 'approved'
                    deposit.save()
                    count += 1

        if count > 0:
            self.message_user(request, f"{count} ta to'lov tasdiqlandi va balansga qo'shildi.", messages.SUCCESS)
        else:
            self.message_user(request, "Tanlangan to'lovlar allaqachon ko'rib chiqilgan.", messages.WARNING)

    @admin.action(description="❌ Rad etish")
    def reject_deposit(self, request, queryset):
        queryset.filter(status='pending').update(status='rejected')
        self.message_user(request, "To'lovlar rad etildi.", messages.ERROR)


@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_select_related = ('user',)
    list_display = ('get_status_icon', 'user', 'amount', 'card_number', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'card_number')
    readonly_fields = ('created_at',)

    actions = ['mark_as_paid', 'reject_withdraw']

    def get_status_icon(self, obj):
        colors = {'pending': '#f59e0b', 'approved': '#10b981', 'rejected': '#ef4444'}
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', colors.get(obj.status),
                           obj.get_status_display())

    get_status_icon.short_description = "Status"

    @admin.action(description="✅ To'lab berildi (Tasdiqlash)")
    def mark_as_paid(self, request, queryset):
        queryset.filter(status='pending').update(status='approved')
        self.message_user(request, "So'rovlar tasdiqlandi.", messages.SUCCESS)

    @admin.action(description="❌ Bekor qilish (Pulni qaytarish)")
    def reject_withdraw(self, request, queryset):
        count = 0
        with transaction.atomic():  # <--- XAVFSIZLIK
            for w in queryset:
                if w.status == 'pending':
                    # Pulni balansga qaytaramiz
                    w.user.profile.balance += w.amount
                    w.user.profile.save()

                    w.status = 'rejected'
                    w.save()
                    count += 1

        if count > 0:
            self.message_user(request, f"{count} ta so'rov bekor qilindi va pul balansga qaytarildi.", messages.ERROR)
        else:
            self.message_user(request, "Tanlangan so'rovlar allaqachon yopilgan.", messages.WARNING)


# =========================================================
# 📦 5. IJTIMOIY VA BOSHQALAR
# =========================================================
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_select_related = ('user', 'project')
    list_display = ('user', 'project', 'amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'project__title')
    readonly_fields = ('user', 'project', 'amount', 'created_at')  # Tarixni o'zgartirib bo'lmasin


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_select_related = ('user', 'project')
    list_display = ('user', 'project', 'body_short', 'created_at')
    search_fields = ('body', 'user__username', 'project__title')
    list_filter = ('created_at',)

    def body_short(self, obj):
        return obj.body[:50] + "..." if len(obj.body) > 50 else obj.body

    body_short.short_description = "Izoh"


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('subject', 'user', 'created_at')
    readonly_fields = ('user', 'subject', 'message', 'created_at')
    list_filter = ('created_at',)


@admin.register(Sync)
class SyncAdmin(admin.ModelAdmin):
    list_display = ('follower', 'following', 'created_at')


@admin.register(CommunityMessage)
class CommunityMessageAdmin(admin.ModelAdmin):
    list_display = ('user', 'body_short', 'created_at')

    def body_short(self, obj):
        return obj.body[:60]