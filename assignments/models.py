from django.db import models
from users.models import CustomUser
from expert_profiles.models import ExpertProfile

class Assignment(models.Model):
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
    )

    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=255)
    description = models.TextField()
    deadline = models.DateTimeField()
    file = models.FileField(upload_to='assignments/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class AssignmentBid(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='bids')
    expert = models.ForeignKey(ExpertProfile, on_delete=models.CASCADE, related_name='bids')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        # Ensures that an expert can only bid once per assignment
        unique_together = ('assignment', 'expert')

    def __str__(self):
        return f"Bid by {self.expert.user.username} on '{self.assignment.title}'"
