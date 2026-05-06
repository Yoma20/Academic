from django.contrib import admin
from .models import ExpertProfile

@admin.register(ExpertProfile)
class ExpertProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'rating', 'available', 'stripe_account_verified']
    list_filter = ['available', 'stripe_account_verified']
    search_fields = ['user__username']