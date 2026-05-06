from django.contrib import admin
from .models import AcademicCategory, Gig, GigPackage, GigExtra

@admin.register(AcademicCategory)
class AcademicCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent']
    list_filter = ['parent']

@admin.register(Gig)
class GigAdmin(admin.ModelAdmin):
    list_display = ['title', 'expert', 'category', 'is_active', 'created_at']

@admin.register(GigPackage)
class GigPackageAdmin(admin.ModelAdmin):
    list_display = ['gig', 'tier', 'price', 'delivery_days']

@admin.register(GigExtra)
class GigExtraAdmin(admin.ModelAdmin):
    list_display = ['gig', 'name', 'price']