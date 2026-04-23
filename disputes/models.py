from django.db import models
from django.conf import settings
from gigs.models import Order


class Dispute(models.Model):
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('evidence_submitted', 'Evidence Submitted'),
        ('under_review', 'Under Admin Review'),
        ('resolved_refund', 'Resolved — Refunded to Student'),
        ('resolved_release', 'Resolved — Released to Expert'),
        ('closed', 'Closed'),
    )
    REASON_CHOICES = (
        ('quality', 'Work quality does not meet requirements'),
        ('rubric', 'Rubric was not followed'),
        ('late', 'Submission was late'),
        ('incomplete', 'Submission was incomplete'),
        ('no_submission', 'Expert never submitted'),
        ('other', 'Other'),
    )

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='dispute',
    )
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='disputes_opened',
    )
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='open')
    resolution_notes = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='disputes_resolved',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Dispute #{self.id} on Order #{self.order.id} [{self.status}]"


class DisputeEvidence(models.Model):
    SUBMITTED_BY_CHOICES = (
        ('student', 'Student'),
        ('expert', 'Expert'),
    )
    dispute = models.ForeignKey(
        Dispute,
        on_delete=models.CASCADE,
        related_name='evidence',
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='dispute_evidence',
    )
    submitted_by_role = models.CharField(max_length=10, choices=SUBMITTED_BY_CHOICES)
    description = models.TextField()
    file = models.FileField(upload_to='disputes/evidence/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Evidence by {self.submitted_by.username} on Dispute #{self.dispute.id}"