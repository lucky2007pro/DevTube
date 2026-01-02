from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import re


# 1. PROFILE (Foydalanuvchi ma'lumotlari + HAMYON)
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # Avatarni ham Cloudinaryga o'tkazamiz (server xotirasini tejash uchun)
    avatar = CloudinaryField('image', default='default.jpg')
    bio = models.TextField(blank=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=100.00)

    def __str__(self):
        return f"{self.user.username} profili"


# 2. LOYIHA MODELI
class Project(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()

    # Asosiy rasm (Thumbnail) - CloudinaryField ishlatamiz
    image = CloudinaryField('image')

    # --- O'ZGARISH: Video fayl YO'Q, faqat YouTube link bor ---
    # (video_file maydoni o'chirib tashlandi)

    youtube_link = models.URLField(max_length=200, help_text="YouTube video ssilkasini qo'ying (Majburiy)")

    # Source code (Zip fayl)
    # Kichik arxivlar uchun FileField qolaversin, lekin Cloudinaryga tushadi
    source_code = models.FileField(upload_to='project_code', blank=True, null=True)

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

        # Har xil turdagi linklardan ID ni ajratib olish (Shorts, Mobile, Watch)
        regex = r'(?:https?:\/\/)?(?:www\.|m\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
        match = re.search(regex, self.youtube_link)

        if match:
            return match.group(1)
        return None

    def __str__(self):
        return self.title


# 3. QO'SHIMCHA RASMLAR (YANGI JADVAL)
# Bitta loyihaga bir nechta rasm (skrinshot) yuklash uchun
class ProjectImage(models.Model):
    project = models.ForeignKey(Project, related_name='images', on_delete=models.CASCADE)
    image = CloudinaryField('image')

    def __str__(self):
        return f"{self.project.title} uchun rasm"


# 4. IZOHLAR
class Comment(models.Model):
    project = models.ForeignKey(Project, related_name='comments', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.project.title}"


# SIGNALS
@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    instance.profile.save()