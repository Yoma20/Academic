from django.db import models
from users.models import CustomUser


class ExpertProfile(models.Model):
    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name='expert_profile'
    )
    field_of_study = models.CharField(max_length=255)
    bio = models.TextField(blank=True)
    available = models.BooleanField(default=True)

    # Overall rating — recalculated by signal on every review save/delete
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)

    # Per-dimension aggregates — recalculated by signal alongside rating
    avg_rubric_adherence = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    avg_timeliness = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    avg_communication = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_reviews = models.PositiveIntegerField(default=0)
    recommendation_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00,
        help_text="Percentage of reviewers who would recommend this expert."
    )

    # Stripe Connect — for payouts (added in escrow feature)
    stripe_account_id = models.CharField(max_length=200, blank=True)
    stripe_account_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"Expert Profile: {self.user.username}"