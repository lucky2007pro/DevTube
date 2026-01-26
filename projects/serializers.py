from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Project, Profile


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

    class Meta:
        model = Profile
        fields = ['username', 'email', 'avatar', 'bio', 'balance']


# Loyihalar uchun
class ProjectSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.username', read_only=True)
    author_avatar = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id', 'title', 'description', 'image', 'price',
            'author_name', 'author_avatar', 'category',
            'youtube_link', 'views', 'created_at'
        ]
        # source_code ni faqat yuklashda ishlatamiz, ko'rishda shart emas
        extra_kwargs = {'source_code': {'write_only': True}}

    def get_author_avatar(self, obj):
        if obj.author.profile.avatar:
            return obj.author.profile.avatar.url
        return ""


# --- projects/serializers.py eng pastiga qo'shing ---

from .models import Comment, Transaction


class CommentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    avatar = serializers.ImageField(source='user.profile.avatar', read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'username', 'avatar', 'body', 'created_at']


class TransactionSerializer(serializers.ModelSerializer):
    project_title = serializers.CharField(source='project.title', read_only=True)

    class Meta:
        model = Transaction
        fields = ['id', 'amount', 'status', 'project_title', 'created_at']