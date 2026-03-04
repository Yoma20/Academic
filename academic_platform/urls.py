"""
URL configuration for academic_platform project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.conf import settings
from django.conf.urls.static import static

# Import the router and the CustomUserViewSet
from rest_framework import routers
from users.views import CustomUserViewSet

# Define a simple root view for the home page.
# This avoids the duplicate function definition.
def index(request):
    return HttpResponse("Welcome to the Academic Platform API! Use the /api/... endpoints to interact with the system.")

# Create a DefaultRouter and register our viewsets with it.
# The router automatically generates URL patterns for viewsets.
router = routers.DefaultRouter()
# The 'users' endpoint will be handled by the CustomUserViewSet.
# This provides the standard RESTful list and detail views at /api/users/users/
router.register(r'users', CustomUserViewSet, basename='users')

# This is the single, complete urlpatterns list for your project.
urlpatterns = [
    # The root URL of the project.
    path('', index, name='index'), 
    
    # The Django admin panel.
    path('admin/', admin.site.urls),
    
    # Include all API URLs from the router.
    # This will automatically create endpoints like /api/users/ for the ViewSet.
    path('api/', include(router.urls)),
    
    # Manually include the custom API URLs for the users app.
    # This is for custom views like register, login, and logout that are not part of the ViewSet.
    path('api/users/', include('users.urls')),

    # Include API URLs for the other applications.
    path('api/assignments/', include('assignments.urls')),
    path('api/expert-profiles/', include('expert_profiles.urls')),
]

# This block serves media files (e.g., user profile pictures) during local development.
# It should not be used in a production environment.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
