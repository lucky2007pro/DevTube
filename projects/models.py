import os
import re
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# --- MUHIM: ZIP fayllar uchun maxsus saqlash turi ---
from cloudinary_storage.storage import RawMediaCloudinaryStorage

# --- 1. PROFILE (Foydalanuvchi ma'lumotlari + HAMYON) ---
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to='avatars/', default='default.jpg')
    bio = models.TextField(blank=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=100.00)

    def __str__(self):
        return f"{self.user.username} profili"


# --- 2. LOYIHA MODELI ---
class Project(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()

    # Asosiy rasm (Thumbnail) - Bu oddiy rasm
    image = models.ImageField(upload_to='project_thumbnails/')

    # YouTube link
    youtube_link = models.URLField(max_length=200, help_text="YouTube video ssilkasini qo'ying (Majburiy)")

    # --- O'ZGARISH SHU YERDA (ZIP FAYL UCHUN) ---
    source_code = models.FileField(
        upload_to='project_code/',
        blank=True,
        null=True,
        storage=RawMediaCloudinaryStorage()  # <--- ZIP fayl xatosini shu tuzatadi
    )

    CATEGORY_CHOICES = [
        ('web', 'Web Dasturlash'),
        ('mobile', 'Mobil Ilovalar'),
        ('ai', 'Sun\'iy Intellekt'),
        ('game', 'O\'yinlar'),
        ('desktop', 'Kompyuter Dasturlari'),
    ]
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='web')
    price = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    views = models.IntegerField(default=0)
    likes = models.ManyToManyField(User, related_name='project_likes', blank=True)
    buyers = models.ManyToManyField(User, related_name='bought_projects', blank=True)

    # --- YOUTUBE ID AJRATIB OLISH ---
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


# --- 3. QO'SHIMCHA RASMLAR ---
class ProjectImage(models.Model):
    project = models.ForeignKey(Project, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='project_screenshots/')

    def __str__(self):
        return f"{self.project.title} uchun rasm"


# --- 4. IZOHLAR ---
class Comment(models.Model):
    project = models.ForeignKey(Project, related_name='comments', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.project.title}"


# --- SIGNALS (Avtomatik profil yaratish) ---
@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    instance.profile.save()