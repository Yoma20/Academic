from django.contrib import admin
from .models import ExpertProfile

@admin.register(ExpertProfile)
class ExpertProfileAdmin(admin.ModelAdmin):
    list_display  = ['user', 'title', 'rating', 'available']
    list_filter   = ['available']
    search_fields = ['user__username']