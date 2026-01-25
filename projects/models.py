import os
import random
import re
import string
from django.urls import reverse
from cloudinary_storage.storage import RawMediaCloudinaryStorage
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


# ==========================================
# 0. YORDAMCHI FUNKSIYALAR (YouTube Style)
# ==========================================

def generate_youtube_id(length=11):
    """Tasodifiy harf va raqamlar generatori"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def validate_file_size(value):
    if value.size > 50 * 1024 * 1024:
        raise ValidationError("Fayl hajmi juda katta! Maksimal hajm: 50 MB")

def validate_file_extension(value):
    ext = os.path.splitext(value.name)[1].lower()
    valid_extensions = ['.zip', '.rar', '.7z', '.tar', '.gz', '.py', '.js', '.html', '.css', '.cpp', '.java', '.dart', '.go', '.php']
    if ext not in valid_extensions:
        raise ValidationError("Faqat kod fayllari yoki arxiv yuklash mumkin.")

# ==========================================
# 1. PROFILE (Foydalanuvchi + Hamyon)
# ==========================================
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_verified = models.BooleanField(default=False)
    avatar = models.ImageField(upload_to='avatars/', default='default.jpg')
    bio = models.TextField(blank=True)
    slug = models.SlugField(unique=True, blank=True, null=True) # User ID: u7H2kLp9
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    telegram_id = models.CharField(max_length=50, blank=True, null=True)
    last_activity = models.DateTimeField(null=True, blank=True)
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_youtube_id(8)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} profili"

# ==========================================
# 2. PROJECT (Asosiy Model)
# ==========================================
class Project(models.Model):
    CATEGORY_CHOICES = [
        ('web', 'Web Dasturlash'), ('mobile', 'Mobil Ilovalar'),
        ('ai', 'Sun\'iy Intellekt'), ('game', 'O\'yinlar'), ('desktop', 'Soft')
    ]

    author = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True, null=True) # Project ID: jNQXAC9IVRw
    description = models.TextField()
    image = models.ImageField(upload_to='project_thumbnails/')
    youtube_link = models.URLField(max_length=200)

    source_code = models.FileField(
        upload_to='project_code/', blank=True, null=True,
        storage=RawMediaCloudinaryStorage(),
        validators=[validate_file_size, validate_file_extension]
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='web')
    price = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    views = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    likes = models.ManyToManyField(User, related_name='project_likes', blank=True)
    saved_by = models.ManyToManyField(User, related_name='saved_projects', blank=True)
    buyers = models.ManyToManyField(User, related_name='bought_projects', blank=True)

    # --- Xavfsizlik Tizimi ---
    is_scanned = models.BooleanField(default=False)
    security_status = models.CharField(max_length=20, default='pending')
    ai_analysis = models.TextField(blank=True, null=True)
    virustotal_link = models.URLField(blank=True, null=True)
    reports_count = models.PositiveIntegerField(default=0)
    is_frozen = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            new_slug = generate_youtube_id(11)
            while Project.objects.filter(slug=new_slug).exists():
                new_slug = generate_youtube_id(11)
            self.slug = new_slug
        super().save(*args, **kwargs)

    @property
    def get_youtube_id(self):
        if not self.youtube_link: return None
        regex = r'(?:https?:\/\/)?(?:www\.|m\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
        match = re.search(regex, self.youtube_link)
        return match.group(1) if match else None

    def __str__(self):
        return self.title
    def get_absolute_url(self):
        return reverse('project_detail', kwargs={'slug': self.slug})
# ==========================================
# 3. IJTIMOIY MODELLAR (Rasmlar, Izohlar, Chat)
# ==========================================

class ProjectImage(models.Model):
    project = models.ForeignKey(Project, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='project_screenshots/')

class Comment(models.Model):
    project = models.ForeignKey(Project, related_name='comments', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class Sync(models.Model):
    follower = models.ForeignKey(Profile, related_name='following', on_delete=models.CASCADE)
    following = models.ForeignKey(Profile, related_name='followers', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')

class CommunityMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class Contact(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contacts')
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

# ==========================================
# 4. MOLIYAVIY MODELLAR (Pul Tizimi)
# ==========================================

class Transaction(models.Model):
    # Statuslar uchun konstantalar (Views da ishlatish uchun qulay)
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    CANCELED = 'canceled'

    STATUS_CHOICES = [
        (PROCESSING, 'Jarayonda'),
        (COMPLETED, 'Muvaffaqiyatli'),
        (CANCELED, 'Bekor qilingan')
    ]

    merchant_trans_id = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PROCESSING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Tranzaksiya {self.id}: {self.amount} - {self.status}"


# models.py ichiga qo'shing

class Withdrawal(models.Model):
    PENDING = 'pending'
    APPROVED = 'approved' # Completed o'rniga Approved ishlating
    REJECTED = 'rejected'

    STATUS_CHOICES = [
        (PENDING, 'Kutilmoqda'),
        (APPROVED, 'To\'lab berildi'), # Approved
        (REJECTED, 'Rad etildi'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='withdrawals')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    card_number = models.CharField(max_length=20)  # Karta raqami
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.amount} ({self.status})"

class Deposit(models.Model):
    STATUS_CHOICES = [('pending', 'Kutilmoqda'), ('approved', 'Tasdiqlandi'), ('rejected', 'Rad etildi')]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    receipt = models.ImageField(upload_to='deposit_receipts/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

# ==========================================
# 5. SIGNALS
# ==========================================
@receiver(post_save, sender=User)
def create_or_save_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()

# projects/models.py ning eng pastiga qo'shing

class Review(models.Model):
    project = models.ForeignKey(Project, related_name='reviews', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # Baho 1 dan 5 gacha bo'ladi
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Bir odam bitta loyihaga faqat bir marta sharh yozishi mumkin
        unique_together = ('project', 'user')

    def __str__(self):
        return f"{self.user.username} - {self.project.title} ({self.rating})"