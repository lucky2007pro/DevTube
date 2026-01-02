import os
from pathlib import Path
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-gknkdin(rj(n$xq7w=6ph=zs)nn7&%!*p5xyn$ul()8v^z+_3l'

# MUHIM: Xatoni aniq ko'rish uchun True turaversin
DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'cloudinary_storage', # Cloudinary staticdan oldin turishi kerak
    'django.contrib.staticfiles',
    'cloudinary',
    'projects',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # STATIC FAYLLAR UCHUN QO'SHILDI
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

# ... (Authentication va Templates qismi o'zgarishsiz qoladi) ...

DATABASES = {
    'default': dj_database_url.config(
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
        conn_max_age=600
    )
}

# --- CLOUDINARY SOZLAMALARI ---
# Eslatma: Kalitlar orasida bo'sh joy yo'qligini tekshiring!
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': 'duy6grluh',
    'API_KEY': '929832358921299',
    'API_SECRET': 'u377zJ4qzYPM9uqKIM37bwspwv0',
}

# Media fayllar uchun Cloudinary
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# Video yuklashda xotira (RAM) xatosini oldini olish uchun
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB dan katta fayllar xotiraga emas, diskka yoziladi
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# settings.py ning eng oxiriga:

LOGIN_REDIRECT_URL = 'home'  # Kirgandan keyin Bosh sahifaga
LOGOUT_REDIRECT_URL = 'home' # Chiqib ketgandan keyin Bosh sahifaga
LOGIN_URL = 'login'          # Login sahifasi manzili