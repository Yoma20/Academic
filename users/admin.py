from django.contrib import admin
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'user_type', 'is_active']
    list_filter = ['user_type', 'is_active']
    search_fields = ['username', 'email']