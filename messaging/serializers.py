from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Conversation, Message

User = get_user_model()


class ParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "user_type"]


class MessageSerializer(serializers.ModelSerializer):
    sender = ParticipantSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ["id", "conversation", "sender", "content", "is_read", "created_at"]
        read_only_fields = ["id", "sender", "is_read", "created_at"]


class ConversationSerializer(serializers.ModelSerializer):
    other_participant = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "other_participant",
            "last_message",
            "unread_count",
            "created_at",
            "updated_at",
        ]

    def get_other_participant(self, obj):
        request = self.context.get("request")
        other = obj.get_other_participant(request.user)
        return ParticipantSerializer(other).data

    def get_last_message(self, obj):
        msg = obj.messages.last()
        if msg:
            return {
                "id": msg.id,
                "content": msg.content[:100],
                "sender_id": msg.sender_id,
                "created_at": msg.created_at,
                "is_read": msg.is_read,
            }
        return None

    def get_unread_count(self, obj):
        request = self.context.get("request")
        return obj.messages.filter(is_read=False).exclude(sender=request.user).count()


class StartConversationSerializer(serializers.Serializer):
    """Used to start a new conversation or retrieve an existing one."""
    recipient_id = serializers.IntegerField()
    initial_message = serializers.CharField(max_length=5000, required=False, allow_blank=True)

    def validate_recipient_id(self, value):
        request = self.context.get("request")
        if value == request.user.id:
            raise serializers.ValidationError("You cannot message yourself.")
        try:
            User.objects.get(pk=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Recipient user not found.")
        return value
