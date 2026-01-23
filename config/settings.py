import os
from pathlib import Path
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# --- XAVFSIZLIK SOZLAMALARI ---
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-default-key-changeme')
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',

    'cloudinary_storage',
    'django.contrib.staticfiles',
    'cloudinary',
    'notifications',
    'projects',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',

    # PROVAYDERLAR
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.github',

    # API & FLUTTER SOZLAMALARI (YANGILANDI)
    'rest_framework',
    'rest_framework.authtoken',  # <-- MUHIM: Token yaratish uchun
    'corsheaders',
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

# --- API SOZLAMALARI (YANGI) ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
}

# --- MA'LUMOTLAR BAZASI ---
DATABASES = {
    'default': dj_database_url.config(
        default=f'sqlite:///{os.path.join(BASE_DIR, "db.sqlite3")}',
        conn_max_age=600
    )
}

# --- STATIC FILES ---
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
WHITENOISE_MANIFEST_STRICT = False

# --- CLOUDINARY ---
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': os.environ.get('CLOUDINARY_API_KEY'),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET'),
}
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# --- QOLGAN SOZLAMALAR ---
LANGUAGE_CODE = 'uz-uz'
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_TZ = True
CSRF_TRUSTED_ORIGINS = ['https://*.onrender.com']
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'
LOGIN_URL = 'login'
SITE_ID = 1
ACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_LOGIN_ON_GET = True

SOCIALACCOUNT_PROVIDERS = {
    'google': {'SCOPE': ['profile', 'email'], 'AUTH_PARAMS': {'access_type': 'online'}},
    'github': {'SCOPE': ['user', 'read:user', 'user:email']},
}

JAZZMIN_SETTINGS = {
    "site_title": "DevTube Admin",
    "site_header": "DevTube",
    "site_brand": "DevTube Boshqaruv",
    "welcome_sign": "Boshqaruv paneliga xush kelibsiz",
    "copyright": "DevTube Ltd",
    "search_model": "auth.User",
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        "projects.Project": "fas fa-video",
        "projects.Profile": "fas fa-id-card",
        "projects.Deposit": "fas fa-arrow-circle-down",
        "projects.Withdrawal": "fas fa-arrow-circle-up",
        "projects.Transaction": "fas fa-history",
        "projects.Comment": "fas fa-comments",
        "projects.Contact": "fas fa-envelope",
        "projects.Sync": "fas fa-sync",
        "projects.CommunityMessage": "fas fa-users",
    },
    "show_sidebar": True,
    "navigation_expanded": True,
    "order_with_respect_to": ["projects", "auth"],
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-dark",
    "accent": "accent-primary",
    "navbar": "navbar-dark",
    "no_navbar_border": False,
    "navbar_fixed": False,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "theme": "darkly",
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    }
}
CORS_ALLOW_ALL_ORIGINS = True