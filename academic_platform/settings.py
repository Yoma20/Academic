from pathlib import Path
import os # Import os module for path manipulation

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# In production, this should be an environment variable or a secret management service.
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-t^7^5n7*m(v2h5*@d(2!n*z9h-h&17z*#d+6i_0)e5#w^!_7')

# SECURITY WARNING: don't run with debug turned on in production!
# Set DEBUG to False in production for security and performance.
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

# In production, replace '*' with your actual domain names (e.g., ['your-frontend-domain.com', 'api.your-backend-domain.com'])
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'web-production-d2ca9.up.railway.app', os.environ.get('RAILWAY_STATIC_URL', '').replace('https://', '')]
if not DEBUG:
    # Example for production:
    # ALLOWED_HOSTS = ['your-production-frontend.com', 'your-production-backend.com']
    pass


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework', # Django REST Framework
    'rest_framework.authtoken', # For token authentication
    'corsheaders', # For handling CORS
    'users', # Your custom users app
    'assignments', # Your custom assignments app
    'expert_profiles', # Your custom expert profiles app
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware', # Essential for many security features
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware', # Add CORS middleware for cross-origin requests
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware', # Protects against Cross-Site Request Forgery
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware', # Protects against clickjacking
]

ROOT_URLCONF = 'academic_platform.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
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

WSGI_APPLICATION = 'academic_platform.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators
# Configure stronger password validation for production
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8, # Enforce a minimum password length
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles') # For collecting static files in production

# Media files (for user uploads like profile pictures, assignment files)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media') # In production, use cloud storage like AWS S3 or Google Cloud Storage


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication', # Recommended for API authentication
        'rest_framework.authentication.SessionAuthentication', # For browsable API and traditional web apps
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated', # Default to requiring authentication for all API views
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10, # Number of items per page for list views
    # Add rate limiting for production to prevent abuse
    # 'DEFAULT_THROTTLE_CLASSES': [
    #     'rest_framework.throttling.AnonRateThrottle',
    #     'rest_framework.throttling.UserRateThrottle'
    # ],
    # 'DEFAULT_THROTTLE_RATES': {
    #     'anon': '100/day',
    #     'user': '1000/day'
    # }
}

# CORS settings - IMPORTANT for frontend communication
# In production, replace "http://localhost:3000" with your actual deployed frontend URL(s).
# For example: CORS_ALLOWED_ORIGINS = ["https://your-github-pages-url.github.io", "https://your-custom-frontend-domain.com"]
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000", # Allow your React development server
]
CORS_ALLOW_CREDENTIALS = True # Allow cookies to be sent with CORS requests (e.g., for session auth)
# If you need to allow all origins during early development (NOT recommended for production):
# CORS_ALLOW_ALL_ORIGINS = True


# --- Production Security Settings ---
# These settings should be uncommented and configured for production environments.
# They are commented out by default to allow easier local development.

# Force all communication over HTTPS
# SECURE_SSL_REDIRECT = True
# SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https') # If behind a proxy like Cloudflare or Nginx

# HTTP Strict Transport Security (HSTS) - Prevents downgrade attacks
# SECURE_HSTS_SECONDS = 31536000 # 1 year
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True # Apply for HSTS preload list (requires specific setup)

# Cookie Security
# CSRF_COOKIE_SECURE = True # Ensure CSRF cookie is only sent over HTTPS
# SESSION_COOKIE_SECURE = True # Ensure session cookie is only sent over HTTPS
# CSRF_COOKIE_HTTPONLY = True # Prevent client-side JavaScript access to CSRF cookie
# SESSION_COOKIE_HTTPONLY = True # Prevent client-side JavaScript access to session cookie

# Prevent content sniffing (e.g., browser interpreting a script as an image)
# SECURE_CONTENT_TYPE_NOSNIFF = True

# Protect against Cross-Site Scripting (XSS) in older browsers
# SECURE_BROWSER_XSS_FILTER = True

# X-Frame-Options - Prevents clickjacking
# X_FRAME_OPTIONS = 'DENY' # Default is 'DENY' in Django 3.0+

# Custom User Model
AUTH_USER_MODEL = 'users.CustomUser'


# CORS Headers configuration
CORS_ALLOWED_ORIGINS = [
    "https://topmark-black.vercel.app",
    "https://topmark-git-main-yoma20s-projects.vercel.app",
    "https://yoma20.github.io",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]

# Allow all Vercel preview deployments automatically
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.vercel\.app$",
]

CORS_ALLOW_CREDENTIALS = True
