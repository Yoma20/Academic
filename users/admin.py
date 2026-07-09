from django.contrib import admin
from .models import CustomUser

from .models import SiteSettings

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ["expert_registration_open"]

    def has_add_permission(self, request):
        # Only one row ever
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
    
@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'user_type', 'is_active']
    list_filter = ['user_type', 'is_active']
    search_fields = ['username', 'email']