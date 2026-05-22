from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-t^7^5n7*m(v2h5*@d(2!n*z9h-h&17z*#d+6i_0)e5#w^!_7')

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

CF_TURNSTILE_SECRET_KEY = os.environ.get('CF_TURNSTILE_SECRET_KEY', '')
CF_TURNSTILE_SITE_KEY = os.environ.get('CF_TURNSTILE_SITE_KEY', '')

DEBUG = os.environ.get('DJANGO_DEBUG', 'False') == 'True'

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

ALLOWED_HOSTS = [
    '127.0.0.1', 'localhost',
    'web-production-d2ca9.up.railway.app',
    'www.topmark.pro',
    'topmark.pro',
    os.environ.get('RAILWAY_STATIC_URL', '').replace('https://', ''),
]

INSTALLED_APPS = [
    'daphne',                                         # ← must be first
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'channels',                                       # ← new
    'corsheaders',
    'users',
    'gigs',
    'feedback',
    'expert_profiles.apps.ExpertProfilesConfig',
    'messaging',
    'disputes',
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@topmark.pro')
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')

EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST          = 'smtp.resend.com'
EMAIL_PORT          = 465
EMAIL_USE_SSL       = True
EMAIL_HOST_USER     = 'resend'
EMAIL_HOST_PASSWORD = RESEND_API_KEY


FRONTEND_URL          = os.environ.get("FRONTEND_URL", "http://localhost:3000")

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'academic_platform.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ── Cache — Redis backend ─────────────────────────────────────────────────────
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://localhost:6379"),
    }
}
# ── ASGI (replaces WSGI_APPLICATION for WebSocket support) ───────────────────
ASGI_APPLICATION = 'academic_platform.asgi.application'

import dj_database_url
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///db.sqlite3')
DATABASES = {
    'default': dj_database_url.config(default=DATABASE_URL)
}

# ── Channel layers — Redis backend ────────────────────────────────────────────
# Railway sets REDIS_URL automatically when you add a Redis service.
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [os.environ.get("REDIS_URL", "redis://localhost:6379")],
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'UTC'
USE_I18N      = True
USE_TZ        = True

STATIC_URL  = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_URL   = '/media/'
MEDIA_ROOT  = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── DRF — session auth only (cookie-based) ───────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}

AUTH_USER_MODEL = 'users.CustomUser'

# ── Cookie security ───────────────────────────────────────────────────────────
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_AGE      = 60 * 60 * 24 * 30
SESSION_COOKIE_SECURE   = True
CSRF_COOKIE_HTTPONLY    = False
CSRF_COOKIE_SAMESITE    = 'None'
CSRF_COOKIE_SECURE      = True

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = [
    "https://topmark-black.vercel.app",
    "https://topmark-git-main-yoma20s-projects.vercel.app",
    "https://yoma20.github.io",
    "https://www.topmark.pro",
    "https://topmark.pro",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.vercel\.app$",
]
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = [
    'https://web-production-d2ca9.up.railway.app',
    'https://www.topmark.pro',
    'https://topmark.pro',
]