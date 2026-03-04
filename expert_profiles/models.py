from django.db import models
from users.models import CustomUser

class ExpertProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='expert_profile')
    field_of_study = models.CharField(max_length=255, help_text="e.g., 'Computer Science', 'Data Analysis'")
    bio = models.TextField(blank=True, help_text="A brief biography of the expert.")
    available = models.BooleanField(default=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Expert Profile: {self.user.username}"

