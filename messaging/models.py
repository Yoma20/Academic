from django.db import models
from django.conf import settings


class Conversation(models.Model):
    """
    A conversation between exactly two users (student ↔ expert).
    Unique constraint prevents duplicate pairs.
    """
    participant_1 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations_as_p1",
    )
    participant_2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations_as_p2",
    )
    # Optional gig context — set when conversation started from a gig page
    gig = models.ForeignKey(
        "gigs.Gig",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="conversations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("participant_1", "participant_2")
        ordering = ["-updated_at"]

    def get_other_participant(self, user):
        return self.participant_2 if self.participant_1 == user else self.participant_1

    def __str__(self):
        return f"Conversation {self.id}: {self.participant_1} ↔ {self.participant_2}"


class Message(models.Model):
    MESSAGE_TYPE_CHOICES = [
        ("text", "Text"),
        ("offer", "Offer"),
    ]

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages",
    )
    content = models.TextField(max_length=5000)
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPE_CHOICES, default="text")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # Link to offer if message_type == "offer"
    offer = models.OneToOneField(
        "Offer",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="message",
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Message {self.id} ({self.message_type}) from {self.sender} in conv {self.conversation_id}"


class Offer(models.Model):
    """
    A custom offer sent by an expert inside a conversation.
    Buyer can accept, decline, or counter-offer.
    """

    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_DECLINED = "declined"
    STATUS_COUNTERED = "countered"
    STATUS_EXPIRED = "expired"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_DECLINED, "Declined"),
        (STATUS_COUNTERED, "Countered"),
        (STATUS_EXPIRED, "Expired"),
    ]

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="offers",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_offers",
    )
    # The gig package this offer is based on (optional — expert might create a custom one)
    package = models.ForeignKey(
        "gigs.GigPackage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="offers",
    )

    # Offer details (may differ from the base package)
    title = models.CharField(max_length=200)
    description = models.TextField(max_length=2000, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    delivery_days = models.PositiveIntegerField()
    revision_number = models.PositiveIntegerField(default=1)

    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_PENDING)

    # If this is a counter-offer, track the parent
    parent_offer = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="counter_offers",
    )

    # Once accepted, the created order is linked here
    order = models.OneToOneField(
        "gigs.Order",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="offer",
    )

    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Offer {self.id} ({self.status}) — ${self.price} by {self.sender}"