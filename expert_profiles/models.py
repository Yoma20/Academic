from django.db import models
from users.models import CustomUser


class ExpertProfile(models.Model):
    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name='expert_profile'
    )
    field_of_study = models.CharField(max_length=255)
    bio             = models.TextField(blank=True)
    title           = models.CharField(max_length=255, blank=True)   # ← NEW
    available       = models.BooleanField(default=True)

    # Skills stored as a comma-separated list (simple, no extra table needed)
    skills          = models.JSONField(default=list, blank=True)      # ← NEW

    # Languages the expert speaks
    languages       = models.JSONField(default=list, blank=True)      # ← NEW

    # Location / country
    country         = models.CharField(max_length=100, blank=True, default='Kenya')  # ← NEW

    # Profile picture URL (populated after avatar upload)
    avatar_url      = models.URLField(blank=True)                     # ← NEW

    # Work experience, education, certifications as structured JSON
    work_experience   = models.JSONField(default=list, blank=True)    # ← NEW
    education         = models.JSONField(default=list, blank=True)    # ← NEW
    certifications    = models.JSONField(default=list, blank=True)    # ← NEW

    # Overall rating — recalculated by signal on every review save/delete
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)

    # Per-dimension aggregates — recalculated by signal alongside rating
    avg_rubric_adherence  = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    avg_timeliness        = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    avg_communication     = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_reviews         = models.PositiveIntegerField(default=0)
    recommendation_rate   = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00,
        help_text="Percentage of reviewers who would recommend this expert."
    )



    def __str__(self):
        return f"Expert Profile: {self.user.username}"