from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.utils import timezone
import random
import string


def generate_otp():
    return ''.join(random.choices(string.digits, k=6))



class SiteSettings(models.Model):
    expert_registration_open = models.BooleanField(
        default=True,
        help_text="Uncheck to stop new expert applications."
    )

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return "Site Settings"

    @classmethod
    def get(cls):
        """Always returns the single settings row, creating it if needed."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
    
class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ('student', 'Student'),
        ('expert', 'Expert'),
        ('admin', 'Admin'),
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='student')
    is_email_verified = models.BooleanField(default=False)
    email_otp = models.CharField(max_length=6, blank=True, null=True)
    email_otp_created_at = models.DateTimeField(blank=True, null=True)
    google_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    profile_picture = models.URLField(blank=True, null=True)

    groups = models.ManyToManyField(
        Group,
        verbose_name=('groups'),
        blank=True,
        help_text=(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name="customuser_set",
        related_query_name="customuser",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=('user permissions'),
        blank=True,
        help_text=('Specific permissions for this user.'),
        related_name="customuser_set",
        related_query_name="customuser",
    )

    def generate_and_save_otp(self):
        self.email_otp = generate_otp()
        self.email_otp_created_at = timezone.now()
        self.save(update_fields=['email_otp', 'email_otp_created_at'])
        return self.email_otp

    def is_otp_valid(self, otp):
        if not self.email_otp or not self.email_otp_created_at:
            return False
        expiry = self.email_otp_created_at + timezone.timedelta(minutes=10)
        return self.email_otp == otp and timezone.now() < expiry

    def __str__(self):
        return self.username