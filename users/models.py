# ======================================================
# File 1: users/models.py
# Description: Defines the custom user model.
# ======================================================
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models

class CustomUser(AbstractUser):
    """
    A custom user model extending Django's AbstractUser.
    This model includes a user_type field to distinguish between
    'student' and 'expert' users.
    """
    USER_TYPE_CHOICES = (
        ('student', 'Student'),
        ('expert', 'Expert'),
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='student')

    # Add related_name to avoid clashes with auth.User's groups and user_permissions
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

    def __str__(self):
        return self.username