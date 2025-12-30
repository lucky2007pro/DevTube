from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


# 1. PROFILE (Foydalanuvchi ma'lumotlari + HAMYON)
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to='profile_images', default='default.jpg')
    bio = models.TextField(blank=True)
    # Hamyon (Boshlanishiga $100 bonus)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=100.00)

    def __str__(self):
        return f"{self.user.username} profili"


# 2. LOYIHA MODELI (+ SOTIB OLGANLAR RO'YXATI)
class Project(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='project_images', blank=True, null=True)
    video_file = models.FileField(upload_to='project_videos', blank=True, null=True)
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

    # Kimlar sotib olgan?
    buyers = models.ManyToManyField(User, related_name='bought_projects', blank=True)

    def __str__(self):
        return self.title


# 3. IZOHLAR
class Comment(models.Model):
    project = models.ForeignKey(Project, related_name='comments', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.project.title}"


# SIGNALS (Profil avtomatik yaratilishi uchun)
@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    instance.profile.save()