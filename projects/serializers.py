from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Project, Profile, Comment, Transaction

# User Registratsiya uchun
class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'password', 'email')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
        return user

# User Profil uchun
class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        # Yangi maydonlar (frozen_balance, is_verified) qo'shildi
        fields = ['username', 'email', 'avatar_url', 'bio', 'balance', 'frozen_balance', 'is_verified', 'telegram_id']

    # Flutter uchun to'liq rasm havolasini yasab beruvchi funksiiya
    def get_avatar_url(self, obj):
        request = self.context.get('request')
        if obj.avatar and hasattr(obj.avatar, 'url'):
            url = obj.avatar.url
            return request.build_absolute_uri(url) if request else url
        return None

# Loyihalar uchun
class ProjectSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.username', read_only=True)
    author_avatar = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()  # <--- Shu qatorni o'zgartirdik

    class Meta:
        model = Project
        fields = [
            'id', 'slug', 'title', 'description', 'image', 'price',
            'author_name', 'author_avatar', 'category',
            'youtube_link', 'views', 'security_status', 'is_scanned', 'created_at'
        ]

    def get_image(self, obj):
        request = self.context.get('request')
        try:
            # Rasm bor-yo'qligini xavfsiz tekshiramiz
            if obj.image and hasattr(obj.image, 'url'):
                url = obj.image.url
                return request.build_absolute_uri(url) if request else url
        except ValueError:
            pass  # Agar rasm fayli topilmasa, qulamasdan pastga o'tib ketadi
        return None

    def get_author_avatar(self, obj):
        request = self.context.get('request')
        try:
            if hasattr(obj.author, 'profile') and obj.author.profile.avatar:
                url = obj.author.profile.avatar.url
                return request.build_absolute_uri(url) if request else url
        except ValueError:
            pass
        return None


# Izohlar uchun
class CommentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    avatar = serializers.SerializerMethodField()  # Xavfsiz usulga o'tkazildi

    class Meta:
        model = Comment
        fields = ['id', 'username', 'avatar', 'body', 'created_at']

    def get_avatar(self, obj):
        request = self.context.get('request')
        if hasattr(obj.user, 'profile') and obj.user.profile.avatar:
            url = obj.user.profile.avatar.url
            return request.build_absolute_uri(url) if request else url
        return None

# Tranzaksiyalar uchun
class TransactionSerializer(serializers.ModelSerializer):
    project_title = serializers.CharField(source='project.title', read_only=True)

    class Meta:
        model = Transaction
        fields = ['id', 'amount', 'status', 'project_title', 'created_at']