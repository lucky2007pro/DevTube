import os
from pathlib import Path
import dj_database_url
import cloudinary
import cloudinary.uploader
import cloudinary.api

# ==============================================
# 1. ASOSIY SOZLAMALAR
# ==============================================

BASE_DIR = Path(__file__).resolve().parent.parent

# Xavfsizlik kaliti
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-default-key-changeme')

# Debug rejimi
DEBUG = True

# Hamma IP lardan kirishga ruxsat
ALLOWED_HOSTS = ['*']

# ==============================================
# 2. INSTALLED APPS
# ==============================================

INSTALLED_APPS = [
    'jazzmin',  # Admin panel dizayni
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.postgres',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',

    # CLOUDINARY
    'cloudinary_storage',
    'cloudinary',

    # 3RD PARTY
    'notifications',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.github',

    # LOCAL APPS
    'projects',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'projects.middleware.UpdateLastActivityMiddleware',
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

# ==============================================
# 3. MA'LUMOTLAR BAZASI (VAQTINCHALIK SOZLAMALAR)
# ==============================================

# Admin yaratish uchun Supabasega to'g'ridan-to'g'ri ulanamiz.
# DIQQAT: Ish bitgach, bu yerni eski holatiga qaytaring!
DATABASES = {
    'default': dj_database_url.config(
        default=f'sqlite:///{os.path.join(BASE_DIR, "db.sqlite3")}',
        conn_max_age=600
    )
}

# ==============================================
# 4. CLOUDINARY (RASMLAR UCHUN)
# ==============================================

# 1. Fayllarni saqlash joyi
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# 2. Django kutubxonasi uchun sozlamalar
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': 'duy6grluh',
    'API_KEY': '929832358921299',
    'API_SECRET': 'u377zJ4qzYPM9uqKIM37bwspwv0'
}

# 3. SDK Konfiguratsiyasi
cloudinary.config(
    cloud_name = 'duy6grluh',
    api_key = '929832358921299',
    api_secret = 'u377zJ4qzYPM9uqKIM37bwspwv0',
    secure = True
)

# Static va Media fayllar manzili
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
WHITENOISE_MANIFEST_STRICT = False

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ==============================================
# 5. API (REST FRAMEWORK)
# ==============================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
}

# CORS
CORS_ALLOW_ALL_ORIGINS = True

# ==============================================
# 6. QOLGAN SOZLAMALAR
# ==============================================

LANGUAGE_CODE = 'uz-uz'
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_TZ = True
CSRF_TRUSTED_ORIGINS = ['https://*.onrender.com', 'http://*.192.168.*.*']
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
X_FRAME_OPTIONS = 'ALLOWALL'

# Auth Redirects
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'
LOGIN_URL = 'login'

# AllAuth settings
SITE_ID = 1
ACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_PROVIDERS = {
    'google': {'SCOPE': ['profile', 'email'], 'AUTH_PARAMS': {'access_type': 'online'}},
    'github': {'SCOPE': ['user', 'read:user', 'user:email']},
}

# Jazzmin Admin Panel
JAZZMIN_SETTINGS = {
    "site_title": "DevTube Admin",
    "site_header": "DevTube",
    "site_brand": "DevTube Boshqaruv",
    "welcome_sign": "Boshqaruv paneliga xush kelibsiz",
    "copyright": "DevTube Ltd",
    "search_model": "auth.User",
    "show_sidebar": True,
    "navigation_expanded": True,
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "projects.Project": "fas fa-video",
    },
}

JAZZMIN_UI_TWEAKS = {
    "theme": "darkly",
}