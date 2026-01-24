import os
import re
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError  # <--- MUHIM: Xatolik qaytarish uchun
from cloudinary_storage.storage import RawMediaCloudinaryStorage


# ==========================================
# 0. VALIDATORLAR (SERVER HIMOYA QATLAMI)
# ==========================================

def validate_file_size(value):
    """Fayl hajmini cheklash (Max: 50 MB)"""
    filesize = value.size
    limit = 50 * 1024 * 1024  # 50 MB
    if filesize > limit:
        raise ValidationError("Fayl hajmi juda katta! Maksimal hajm: 50 MB")

def validate_file_extension(value):
    """Faqat ruxsat etilgan fayl turlarini tekshirish"""
    ext = os.path.splitext(value.name)[1]  # Fayl kengaytmasini olamiz
    valid_extensions = [
        '.zip', '.rar', '.7z', '.tar', '.gz',  # Arxivlar
        '.py', '.js', '.html', '.css', '.cpp', '.java', '.c', '.cs', '.php', '.sql', '.json', '.xml', '.txt', '.md', # Kodlar
        '.ipynb', '.dart', '.go', '.rs', '.swift', '.kt' # Qo'shimcha tillar
    ]
    if not ext.lower() in valid_extensions:
        raise ValidationError("Ruxsat etilmagan fayl turi! Faqat kod fayllari yoki arxiv (.zip, .rar) yuklash mumkin.")


# ==========================================
# 1. PROFILE (Foydalanuvchi ma'lumotlari + HAMYON)
# ==========================================
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to='avatars/', default='default.jpg')
    bio = models.TextField(blank=True)

    # Hamyon balansi (Default 0$)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.user.username} profili"


# ==========================================
# 2. LOYIHA MODELI (ASOSIY)
# ==========================================
class Project(models.Model):
    CATEGORY_CHOICES = [
        ('web', 'Web Dasturlash'),
        ('mobile', 'Mobil Ilovalar'),
        ('ai', 'Sun\'iy Intellekt'),
        ('game', 'O\'yinlar'),
        ('desktop', 'Kompyuter Dasturlari'),
    ]

    author = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='project_thumbnails/')
    youtube_link = models.URLField(max_length=200, help_text="YouTube video ssilkasini qo'ying (Majburiy)")

    # Fayl va Statistika (VALIDATORLAR QO'SHILDI)
    source_code = models.FileField(
        upload_to='project_code/',
        blank=True,
        null=True,
        storage=RawMediaCloudinaryStorage(),
        validators=[validate_file_size, validate_file_extension]  # <--- HIMOYA YOQILDI
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='web')
    price = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    views = models.IntegerField(default=0)

    # Ijtimoiy aloqalar
    likes = models.ManyToManyField(User, related_name='project_likes', blank=True)
    saved_by = models.ManyToManyField(User, related_name='saved_projects', blank=True)
    buyers = models.ManyToManyField(User, related_name='bought_projects', blank=True)

    # --- XAVFSIZLIK TIZIMI ---
    is_scanned = models.BooleanField(default=False)  # Tekshirildimi?
    security_status = models.CharField(
        max_length=20,
        choices=[
            ('safe', 'Xavfsiz'),
            ('warning', 'Shubhali'),
            ('danger', 'Xavfli'),
            ('pending', 'Tekshirilmoqda')
        ],
        default='pending'
    )
    ai_analysis = models.TextField(blank=True, null=True)  # Gemini xulosasi
    virustotal_link = models.URLField(blank=True, null=True)  # VirusTotal hisoboti

    # Bloklash tizimi
    reports_count = models.PositiveIntegerField(default=0)
    is_frozen = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    @property
    def get_youtube_id(self):
        if not self.youtube_link:
            return None
        regex = r'(?:https?:\/\/)?(?:www\.|m\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
        match = re.search(regex, self.youtube_link)
        if match:
            return match.group(1)
        return None

    def __str__(self):
        return self.title


# ==========================================
# 3. QO'SHIMCHA RASMLAR
# ==========================================
class ProjectImage(models.Model):
    project = models.ForeignKey(Project, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='project_screenshots/')

    def __str__(self):
        return f"{self.project.title} uchun rasm"


# ==========================================
# 4. IZOHLAR
# ==========================================
class Comment(models.Model):
    project = models.ForeignKey(Project, related_name='comments', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.project.title}"


# ==========================================
# 5. OBUNALAR (FOLLOWING)
# ==========================================
class Sync(models.Model):
    follower = models.ForeignKey(Profile, related_name='following', on_delete=models.CASCADE)
    following = models.ForeignKey(Profile, related_name='followers', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.follower.user.username} -> {self.following.user.username}"


# ==========================================
# 6. CHAT
# ==========================================
class CommunityMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.username}: {self.body[:20]}"


# ==========================================
# 7. ALOQA (CONTACT)
# ==========================================
class Contact(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contacts')
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.subject}"


# ==========================================
# MOLIYAVIY MODELLAR (PUL TIZIMI)
# ==========================================

# --- 8. TRANZAKSIYALAR ---
class Transaction(models.Model):
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    CANCELED = 'canceled'

    STATUS_CHOICES = [
        (PROCESSING, 'Jarayonda'),
        (COMPLETED, 'Muvaffaqiyatli'),
        (CANCELED, 'Bekor qilingan'),
    ]

    click_trans_id = models.CharField(max_length=255, blank=True, null=True)
    merchant_trans_id = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PROCESSING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.merchant_trans_id} - {self.status}"


# --- 9. PUL YECHISH (WITHDRAWAL) ---
class Withdrawal(models.Model):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'

    STATUS_CHOICES = [
        (PENDING, 'Kutilmoqda'),
        (APPROVED, 'To\'lab berildi'),
        (REJECTED, 'Rad etildi'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    card_number = models.CharField(max_length=16, help_text="Karta raqami (16 ta raqam)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.amount} ({self.status})"


# --- 10. DEPOZIT (PUL KIRITISH) ---
class Deposit(models.Model):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'

    STATUS_CHOICES = [
        (PENDING, 'Kutilmoqda'),
        (APPROVED, 'Tasdiqlandi'),
        (REJECTED, 'Rad etildi'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Chek rasmi va izoh
    receipt = models.ImageField(upload_to='deposit_receipts/', blank=True, null=True)
    message = models.CharField(max_length=255, blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.amount}"


# ==========================================
# SIGNALS (AVTOMATIK PROFIL YARATISH)
# ==========================================
@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    instance.profile.save()