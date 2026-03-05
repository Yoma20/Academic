"""
URL configuration for academic_platform project.
"""
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.conf import settings
from django.conf.urls.static import static


def index(request):
    return HttpResponse("Welcome to the Academic Platform API!")


urlpatterns = [
    path('', index, name='index'),
    path('admin/', admin.site.urls),
    path('api/users/', include('users.urls')),
    path('api/assignments/', include('assignments.urls')),
    path('api/expert-profiles/', include('expert_profiles.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
