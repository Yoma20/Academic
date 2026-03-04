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
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '.onrender.com']
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
    "http://localhost:3000",
    "https://topmark-black.vercel.app/",  # your Vercel frontend
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

# academic_platform/urls.py
"""
URL configuration for academic_platform project.

The `urlpatterns` list routes URLs to views. For more information please see:
    [https://docs.djangoproject.com/en/5.0/topics/http/urls/](https://docs.djangoproject.com/en/5.0/topics/http/urls/)
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings # Import settings
from django.conf.urls.static import static # Import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/users/', include('users.urls')),
    path('api/assignments/', include('assignments.urls')),
    path('api/expert-profiles/', include('expert_profiles.urls')), # Include expert_profiles URLs
]

# Serve media files during development
# In production, these should be served from a dedicated service like AWS S3 or Google Cloud Storage.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# users/models.py
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models

class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ('student', 'Student'),
        ('expert', 'Expert'),
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='student')

    # Add related_name to avoid clashes with auth.User's groups and user_permissions
    # These are necessary when using a custom user model and also using Django's default Group/Permission models.
    groups = models.ManyToManyField(
        Group,
        verbose_name=('groups'),
        blank=True,
        help_text=(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name="customuser_set", # Custom related_name to prevent clashes
        related_query_name="customuser",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=('user permissions'),
        blank=True,
        help_text=('Specific permissions for this user.'),
        related_name="customuser_set", # Custom related_name to prevent clashes
        related_query_name="customuser",
    )

    def __str__(self):
        return self.username


# users/serializers.py
from rest_framework import serializers
from .models import CustomUser

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'user_type', 'password']
        # Ensure password is write-only and not returned in responses
        extra_kwargs = {'password': {'write_only': True, 'min_length': 8}}

    def create(self, validated_data):
        # Use create_user to ensure password is properly hashed
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            user_type=validated_data.get('user_type', 'student') # Default to student if not provided
        )
        return user
import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600,
    )
}
```
5. Add to your Start Command:
```
python manage.py migrate && gunicorn academic_platform.wsgi --bind 0.0.0.0:$PORT

