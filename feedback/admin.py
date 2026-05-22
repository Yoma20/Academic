from django.contrib import admin
from .models import Feedback


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display  = ('report_type', 'short_message', 'created_at')
    list_filter   = ('report_type',)
    search_fields = ('message',)
    readonly_fields = ('report_type', 'message', 'created_at')

    def short_message(self, obj):
        return obj.message[:80]
    short_message.short_description = 'Message'