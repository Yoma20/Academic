# ======================================================
# File 1: academic_platform/urls.py (Main project urls.py)
# Description: Defines the main URL patterns for the project.
# This file remains the same and is correct.
# ======================================================
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # The 'api/' prefix is a good practice for all API endpoints.
    # The 'users/' prefix here directs all URLs starting with
    # 'api/users/' to the users app's URL patterns.
    path('api/users/', include('users.urls')),
]

# ======================================================
# File 2: users/urls.py (Users app urls.py)
# Description: Defines the URL patterns for the users app.
# The custom paths are now combined with the router's URLs
# in a more robust and unambiguous way.
# ======================================================
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomUserViewSet, RegisterView, LoginView, LogoutView

# Create a router instance to handle our ViewSet URLs
router = DefaultRouter()
# Register the CustomUserViewSet with the router.
router.register(r'', CustomUserViewSet, basename='user')

# Define the custom URLs for authentication separately.
auth_urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]

# Combine the custom authentication URLs and the router's URLs.
# This is a robust way to ensure no recursive include issues.
urlpatterns = auth_urlpatterns + router.urls

