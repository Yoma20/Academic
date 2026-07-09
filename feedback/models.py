from django.db import models


class Feedback(models.Model):
    REPORT_TYPES = [
        ('bug',      'Bug Report'),
        ('idea',     'Feature Idea'),
        ('category', 'Missing Category'),
        ('other',    'Other'),
    ]

    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    message     = models.TextField()
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Feedback'

    def __str__(self):
        return f"[{self.get_report_type_display()}] {self.message[:60]}"