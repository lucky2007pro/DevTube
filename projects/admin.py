from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html  # HTML (Rasm/Rang) uchun kerak
from django.contrib.auth.models import Group

# Modellar importi
from .models import (
    Profile, Project, ProjectImage, Comment, Sync,
    CommunityMessage, Contact, Transaction, Withdrawal, Deposit
)

# =========================================================
# 🎨 1. ADMIN PANEL DIZAYNI (HEADER & TITLE)
# =========================================================
admin.site.site_header = "DevTube Boshqaruv Paneli"
admin.site.site_title = "DevTube Admin"
admin.site.index_title = "Statistika va Boshqaruv"

# Guruhlar (Groups) bizga kerak emas, chalg'itmasligi uchun o'chiramiz
admin.site.unregister(Group)


# =========================================================
# 👤 2. FOYDALANUVCHILAR (PROFIL)
# =========================================================
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('get_avatar', 'user', 'get_balance_styled', 'bio_short')
    list_display_links = ('user', 'get_avatar')
    search_fields = ('user__username', 'user__email')
    list_per_page = 20

    # RASM (Avatar) - Dumaloq qilib ko'rsatish
    def get_avatar(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover; border: 2px solid #ddd;" />',
                obj.avatar.url
            )
        return "👤"
    get_avatar.short_description = "Rasm"

    # BALANS - Yashil va Qalin rangda
    def get_balance_styled(self, obj):
        return format_html(
            '<span style="color: green; font-weight: bold; font-size: 14px;">${}</span>',
            obj.balance
        )
    get_balance_styled.short_description = "Hamyon"

    # BIO - Juda uzun bo'lsa qisqartirish
    def bio_short(self, obj):
        return obj.bio[:50] + "..." if obj.bio else "-"
    bio_short.short_description = "Haqida"

    # ACTION: Balansni 0 qilish
    actions = ['reset_balance']
    def reset_balance(self, request, queryset):
        cnt = queryset.update(balance=0)
        self.message_user(request, f"{cnt} ta foydalanuvchi balansi tozalandi.", messages.WARNING)
    reset_balance.short_description = "🗑 Balansni 0 qilish"


# =========================================================
# 🎬 3. LOYIHALAR (PROJECTS) - YouTube Style
# =========================================================
class ProjectImageInline(admin.TabularInline):
    model = ProjectImage
    extra = 1
    classes = ('collapse',) # Joyni tejash uchun yig'ib qo'yish

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    inlines = [ProjectImageInline]
    list_display = ('get_thumbnail', 'title', 'author', 'get_price_tag', 'views', 'created_at')
    list_filter = ('category', 'created_at')
    search_fields = ('title', 'author__username')
    list_per_page = 15

    # LOYIHA RASMI (Thumbnail)
    def get_thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 80px; height: 45px; border-radius: 5px; object-fit: cover;" />',
                obj.image.url
            )
        return "🎬"
    get_thumbnail.short_description = "Muqova"

    # NARX (Free yoki Summa)
    def get_price_tag(self, obj):
        if obj.price == 0:
            return format_html('<span style="background: #28a745; color: white; padding: 3px 8px; border-radius: 10px; font-size: 11px;">Free</span>')
        return format_html('<span style="font-weight: bold;">${}</span>', obj.price)
    get_price_tag.short_description = "Narx"


# =========================================================
# 💰 4. DEPOZITLAR (PUL KIRITISH) - Chek bilan
# =========================================================
@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = ('get_status_icon', 'user', 'amount', 'get_receipt_preview', 'created_at')
    list_filter = ('status', 'created_at')
    list_display_links = ('user',)
    actions = ['approve_deposit', 'reject_deposit']

    # STATUS IKONKALARI (🟢 🟡 🔴)
    def get_status_icon(self, obj):
        colors = {
            'pending': '#ffc107',  # Sariq
            'approved': '#28a745', # Yashil
            'rejected': '#dc3545'  # Qizil
        }
        icons = {
            'pending': '⏳',
            'approved': '✅',
            'rejected': '❌'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            colors.get(obj.status, 'black'),
            icons.get(obj.status, ''),
            obj.get_status_display()
        )
    get_status_icon.short_description = "Holat"

    # CHEK (Skrinshot) - Katta qilish imkoni bilan
    def get_receipt_preview(self, obj):
        if obj.receipt:
            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" style="width: 100px; height: auto; border: 1px solid #ccc; border-radius: 5px;" title="Kattalashtirish uchun bosing" />'
                '</a>',
                obj.receipt.url, obj.receipt.url
            )
        return "📄 Chek yo'q"
    get_receipt_preview.short_description = "To'lov Cheki"

    # ACTION: Tasdiqlash
    def approve_deposit(self, request, queryset):
        count = 0
        for deposit in queryset:
            if deposit.status == Deposit.PENDING:
                profile = deposit.user.profile
                profile.balance += deposit.amount
                profile.save()
                deposit.status = Deposit.APPROVED
                deposit.save()
                count += 1
        self.message_user(request, f"{count} ta to'lov tasdiqlandi.", messages.SUCCESS)
    approve_deposit.short_description = "✅ Tasdiqlash (Balansga qo'shish)"

    # ACTION: Rad etish
    def reject_deposit(self, request, queryset):
        queryset.update(status=Deposit.REJECTED)
        self.message_user(request, "Tanlanganlar rad etildi.", messages.ERROR)
    reject_deposit.short_description = "❌ Rad etish"


# =========================================================
# 💸 5. PUL YECHISH (WITHDRAWAL)
# =========================================================
@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ('get_status_icon', 'user', 'amount', 'card_display', 'created_at')
    list_filter = ('status',)
    actions = ['mark_as_paid', 'mark_as_rejected']

    # Karta raqamini chiroyli ko'rsatish (Oxirgi 4 tasi)
    def card_display(self, obj):
        return f"**** {obj.card_number[-4:]}"
    card_display.short_description = "Karta"

    # Status Rangli (Tepadagi funksiyani qayta yozamiz yoki alohida)
    def get_status_icon(self, obj):
        colors = {'pending': 'orange', 'approved': 'green', 'rejected': 'red'}
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    get_status_icon.short_description = "Status"

    def mark_as_paid(self, request, queryset):
        queryset.update(status=Withdrawal.APPROVED)
        self.message_user(request, "To'lab berildi deb belgilandi.", messages.SUCCESS)
    mark_as_paid.short_description = "✅ To'lab berildi"

    def mark_as_rejected(self, request, queryset):
        count = 0
        for w in queryset:
            if w.status == Withdrawal.PENDING:
                w.user.profile.balance += w.amount # Qaytarish
                w.user.profile.save()
                w.status = Withdrawal.REJECTED
                w.save()
                count += 1
        self.message_user(request, f"{count} ta so'rov rad etildi (Pul qaytarildi).", messages.ERROR)
    mark_as_rejected.short_description = "❌ Rad etish (Pulni qaytarish)"


# =========================================================
# 📦 6. BOSHQALAR
# =========================================================
@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('subject', 'user', 'created_at')
    list_filter = ('created_at',)

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('merchant_trans_id', 'user', 'amount', 'status')

# Qolganlarni shunchaki ro'yxatga olamiz
admin.site.register(Comment)
admin.site.register(Sync)
admin.site.register(CommunityMessage)