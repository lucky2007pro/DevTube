import os
from pathlib import Path
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# --- XAVFSIZLIK SOZLAMALARI ---
# GitHubda "Secret Key exposed" demasligi uchun kalitni Environmentdan olamiz.
# Agar topilmasa (Localda), default kalit ishlatadi.
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-default-key-changeme')

# Renderda DEBUG=False bo'lishi kerak.
# "True" qilib qo'ysangiz xatolarni ko'rasiz, lekin Production uchun "False" xavfsizroq.
# Quyidagi qator: Agar Renderda bo'lsak False, kompyuterda bo'lsak True bo'ladi.
DEBUG = 'RENDER' not in os.environ

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'jazzmin',  # Admin panel dizayni
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',

    # DIQQAT: Cloudinary staticdan oldin turishi SHART
    'cloudinary_storage',
    'django.contrib.staticfiles',
    'cloudinary',

    # Loyiha ilovalari
    'projects',

    # Allauth (Login/Register uchun)
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise - Static fayllar (CSS/JS) uchun
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Allauth middleware
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# --- MA'LUMOTLAR BAZASI ---
# Renderda avtomatik PostgreSQL, kompyuterda SQLite ishlatadi
DATABASES = {
    'default': dj_database_url.config(
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
        conn_max_age=600
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'uz-uz'  # Tilni o'zbekcha qildim
TIME_ZONE = 'Asia/Tashkent'  # Vaqt mintaqasi
USE_I18N = True
USE_TZ = True

# --- STATIC FILES (CSS, JavaScript, Images) ---
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

if os.path.exists(os.path.join(BASE_DIR, 'static')):
    STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
else:
    STATICFILES_DIRS = []

# WhiteNoise orqali fayllarni siqish va keshlash
# Agar "map not found" xatosi chiqsa, 'whitenoise.storage.CompressedStaticFilesStorage' ishlating
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# --- CLOUDINARY SOZLAMALARI (GitHub Xavfsizligi) ---
# Bu yerda hech qanday raqam yozilmagan. Hammasi Render Environmentdan olinadi.
# Render Environment Variable nomlari aynan shunday bo'lishi kerak:
# 1. CLOUDINARY_CLOUD_NAME
# 2. CLOUDINARY_API_KEY
# 3. CLOUDINARY_API_SECRET
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': os.environ.get('CLOUDINARY_API_KEY'),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET'),
}

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# Katta fayllarni yuklashda xatolik oldini olish
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login sozlamalari
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'
LOGIN_URL = 'login'

# Allauth sozlamalari
SITE_ID = 1
ACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_LOGIN_ON_GET = True