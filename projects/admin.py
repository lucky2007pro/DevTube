from django.contrib import admin
from django.contrib import messages
from .models import (
    Profile, Project, ProjectImage, Comment, Sync,
    CommunityMessage, Contact, Transaction, Withdrawal, Deposit
)


# --- 1. PROFILE (Balansni ko'rish uchun) ---
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'avatar_preview')
    search_fields = ('user__username', 'bio')

    # 1. YANGI TUGMA (Action)
    actions = ['reset_balance_to_zero']

    def reset_balance_to_zero(self, request, queryset):
        # Tanlanganlarning balansini 0 ga tushiradi
        updated_count = queryset.update(balance=0)
        self.message_user(request, f"{updated_count} ta foydalanuvchi balansi 0 ga tushirildi.", messages.SUCCESS)

    reset_balance_to_zero.short_description = "💰 Balansni 0 qilish (Reset)"

    # 2. ESKI FUNKSIYANGIZ (Avatar bor/yo'qligini ko'rsatish)
    def avatar_preview(self, obj):
        if obj.avatar:
            return "Rasm bor"
        return "Yo'q"

    avatar_preview.short_description = "Avatar"


# --- 2. LOYIHA VA RASMLARI ---
class ProjectImageInline(admin.TabularInline):
    model = ProjectImage
    extra = 1


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    inlines = [ProjectImageInline]
    list_display = ('title', 'author', 'price', 'category', 'views', 'created_at')
    list_filter = ('category', 'created_at')
    search_fields = ('title', 'description', 'author__username')


# --- 3. DEPOZIT (PUL KIRITISH) - ENG MUHIMI ---
@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'transaction_id', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'transaction_id')

    actions = ['approve_deposit', 'reject_deposit']

    # ✅ 1. TASDIQLASH (Balansga pul qo'shadi)
    def approve_deposit(self, request, queryset):
        count = 0
        for deposit in queryset:
            if deposit.status == Deposit.PENDING:
                # 1. Balansga qo'shish
                profile = deposit.user.profile
                profile.balance += deposit.amount
                profile.save()

                # 2. Statusni o'zgartirish
                deposit.status = Deposit.APPROVED
                deposit.save()
                count += 1

        if count > 0:
            self.message_user(request, f"{count} ta to'lov tasdiqlandi va balansga qo'shildi!", messages.SUCCESS)
        else:
            self.message_user(request, "Tanlanganlar orasida 'Kutilmoqda' statusidagilar yo'q.", messages.WARNING)

    approve_deposit.short_description = "✅ Tasdiqlash va Balansga qo'shish"

    # ❌ 2. RAD ETISH
    def reject_deposit(self, request, queryset):
        rows_updated = queryset.update(status=Deposit.REJECTED)
        self.message_user(request, f"{rows_updated} ta so'rov rad etildi.", messages.ERROR)

    reject_deposit.short_description = "❌ Rad etish"


# --- 4. PUL YECHISH (WITHDRAWAL) ---
@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'card_number', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'card_number')

    actions = ['mark_as_paid', 'mark_as_rejected']

    def mark_as_paid(self, request, queryset):
        queryset.update(status=Withdrawal.APPROVED)
        self.message_user(request, "Tanlanganlarga to'lov qilindi deb belgilandi.", messages.SUCCESS)

    mark_as_paid.short_description = "✅ To'lov qilindi (Tasdiqlash)"

    def mark_as_rejected(self, request, queryset):
        # Agar rad etilsa, pulni balansga QAYTARISH kerak
        count = 0
        for withdrawal in queryset:
            if withdrawal.status == Withdrawal.PENDING:
                profile = withdrawal.user.profile
                profile.balance += withdrawal.amount  # Pulni qaytarish
                profile.save()

                withdrawal.status = Withdrawal.REJECTED
                withdrawal.save()
                count += 1
        self.message_user(request, f"{count} ta so'rov rad etildi va pullar balansga qaytarildi.", messages.INFO)

    mark_as_rejected.short_description = "❌ Rad etish va Pulni qaytarish"


# --- 5. BOSHQA MODELLAR ---
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('merchant_trans_id', 'user', 'amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('merchant_trans_id', 'user__username')
    readonly_fields = ('merchant_trans_id', 'click_trans_id', 'amount', 'user', 'project')


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('user', 'subject', 'created_at')
    search_fields = ('user__username', 'subject', 'message')
    list_filter = ('created_at',)


admin.site.register(Comment)
admin.site.register(Sync)
admin.site.register(CommunityMessage)