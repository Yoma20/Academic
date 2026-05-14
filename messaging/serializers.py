from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Conversation, Message, Offer

User = get_user_model()


class ParticipantSerializer(serializers.ModelSerializer):
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "user_type", "profile_picture"]

def get_profile_picture(self, user):
    if user.user_type == "expert":
        try:
            url = user.expert_profile.avatar_url
            if url:
                return url
        except Exception:
            pass
    if user.profile_picture:
        return user.profile_picture  # already a full URL string
    return None


class OfferSerializer(serializers.ModelSerializer):
    sender = serializers.SerializerMethodField()

    def get_sender(self, obj):
        return ParticipantSerializer(obj.sender, context=self.context).data

    class Meta:
        model = Offer
        fields = [
            "id",
            "sender",
            "title",
            "description",
            "price",
            "delivery_days",
            "revision_number",
            "status",
            "package",
            "parent_offer",
            "order",
            "expires_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "sender", "status", "order", "created_at", "updated_at"]


class MessageSerializer(serializers.ModelSerializer):
    sender = serializers.SerializerMethodField()
    offer = serializers.SerializerMethodField()

    def get_sender(self, obj):
        return ParticipantSerializer(obj.sender, context=self.context).data

    def get_offer(self, obj):
        if obj.offer:
            return OfferSerializer(obj.offer, context=self.context).data
        return None

    class Meta:
        model = Message
        fields = [
            "id",
            "conversation",
            "sender",
            "content",
            "message_type",
            "offer",
            "is_read",
            "created_at",
        ]
        read_only_fields = ["id", "is_read", "created_at", "message_type"]


class ConversationSerializer(serializers.ModelSerializer):
    other_participant = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    gig_title = serializers.SerializerMethodField()
    pending_offer = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "other_participant",
            "last_message",
            "unread_count",
            "gig_title",
            "pending_offer",
            "created_at",
            "updated_at",
        ]

    def get_other_participant(self, obj):
        request = self.context.get("request")
        other = obj.get_other_participant(request.user)
        return ParticipantSerializer(other, context=self.context).data

    def get_last_message(self, obj):
        msg = obj.messages.last()
        if msg:
            return {
                "id": msg.id,
                "content": msg.content[:100],
                "message_type": msg.message_type,
                "sender_id": msg.sender_id,
                "created_at": msg.created_at,
                "is_read": msg.is_read,
            }
        return None

    def get_unread_count(self, obj):
        request = self.context.get("request")
        return obj.messages.filter(is_read=False).exclude(sender=request.user).count()

    def get_gig_title(self, obj):
        return obj.gig.title if obj.gig else None

    def get_pending_offer(self, obj):
        """Return the most recent pending offer in this conversation, if any."""
        offer = obj.offers.filter(status=Offer.STATUS_PENDING).order_by("-created_at").first()
        if offer:
            return OfferSerializer(offer).data
        return None


class StartConversationSerializer(serializers.Serializer):
    """Used to start a new conversation or retrieve an existing one."""
    recipient_id = serializers.IntegerField()
    initial_message = serializers.CharField(max_length=5000, required=False, allow_blank=True)
    gig_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_recipient_id(self, value):
        request = self.context.get("request")
        if value == request.user.id:
            raise serializers.ValidationError("You cannot message yourself.")
        try:
            User.objects.get(pk=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Recipient user not found.")
        return value


class SendOfferSerializer(serializers.Serializer):
    """Validates the payload when an expert sends a custom offer."""
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    price = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=1)
    delivery_days = serializers.IntegerField(min_value=1, max_value=365)
    revision_number = serializers.IntegerField(min_value=0, max_value=20)
    package_id = serializers.IntegerField(required=False, allow_null=True)
    parent_offer_id = serializers.IntegerField(required=False, allow_null=True)


class RespondOfferSerializer(serializers.Serializer):
    """Validates accept / decline responses from the buyer."""
    action = serializers.ChoiceField(choices=["accept", "decline"])