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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # bumped on every new message

    class Meta:
        # Enforce that (A, B) and (B, A) can't both exist — handled in the serializer
        unique_together = ("participant_1", "participant_2")
        ordering = ["-updated_at"]

    def get_other_participant(self, user):
        return self.participant_2 if self.participant_1 == user else self.participant_1

    def __str__(self):
        return f"Conversation {self.id}: {self.participant_1} ↔ {self.participant_2}"


class Message(models.Model):
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
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Message {self.id} from {self.sender} in conv {self.conversation_id}"
