from django.contrib.auth import get_user_model
from django.db import models as db_models
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Conversation, Message
from .serializers import (
    ConversationSerializer,
    MessageSerializer,
    StartConversationSerializer,
)

User = get_user_model()


class IsConversationParticipant(permissions.BasePermission):
    """Only allows access to users who are a participant in the conversation."""

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Conversation):
            return obj.participant_1 == request.user or obj.participant_2 == request.user
        if isinstance(obj, Message):
            conv = obj.conversation
            return conv.participant_1 == request.user or conv.participant_2 == request.user
        return False


class ConversationListView(generics.ListAPIView):
    """
    GET /api/messaging/conversations/
    Returns all conversations for the authenticated user, newest first.
    """
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return (
            Conversation.objects.filter(
                db_models.Q(participant_1=user) | db_models.Q(participant_2=user)
            )
            .select_related("participant_1", "participant_2")
            .prefetch_related("messages")
            .order_by("-updated_at")
        )


class StartConversationView(APIView):
    """
    POST /api/messaging/conversations/start/
    Body: { recipient_id, initial_message? }
    Creates or retrieves a conversation and optionally sends the first message.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = StartConversationSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        recipient_id = serializer.validated_data["recipient_id"]
        initial_message = serializer.validated_data.get("initial_message", "").strip()
        recipient = User.objects.get(pk=recipient_id)
        user = request.user

        # Ensure canonical ordering so (A,B) and (B,A) map to the same row
        p1, p2 = (user, recipient) if user.id < recipient.id else (recipient, user)

        conversation, created = Conversation.objects.get_or_create(
            participant_1=p1, participant_2=p2
        )

        if initial_message:
            Message.objects.create(
                conversation=conversation,
                sender=user,
                content=initial_message,
            )
            # Bump updated_at so it sorts to the top
            conversation.save()

        out = ConversationSerializer(conversation, context={"request": request})
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(out.data, status=status_code)


class MessageListView(generics.ListAPIView):
    """
    GET /api/messaging/conversations/<conv_id>/messages/
    Returns all messages in a conversation (oldest first).
    Marks unread messages as read on retrieval.
    """
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated, IsConversationParticipant]

    def get_queryset(self):
        conv_id = self.kwargs["conv_id"]
        user = self.request.user

        try:
            conversation = Conversation.objects.get(pk=conv_id)
        except Conversation.DoesNotExist:
            return Message.objects.none()

        self.check_object_permissions(self.request, conversation)

        # Mark incoming messages as read
        Message.objects.filter(
            conversation=conversation, is_read=False
        ).exclude(sender=user).update(is_read=True)

        return Message.objects.filter(conversation=conversation).select_related("sender")


class SendMessageView(APIView):
    """
    POST /api/messaging/conversations/<conv_id>/messages/
    Body: { content }
    Sends a message in an existing conversation.
    """
    permission_classes = [permissions.IsAuthenticated, IsConversationParticipant]

    def post(self, request, conv_id):
        try:
            conversation = Conversation.objects.get(pk=conv_id)
        except Conversation.DoesNotExist:
            return Response({"detail": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, conversation)

        content = request.data.get("content", "").strip()
        if not content:
            return Response({"detail": "Message content cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)
        if len(content) > 5000:
            return Response({"detail": "Message too long (max 5000 characters)."}, status=status.HTTP_400_BAD_REQUEST)

        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=content,
        )
        # Bump conversation updated_at for ordering
        conversation.save()

        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)


class UnreadCountView(APIView):
    """
    GET /api/messaging/unread-count/
    Returns the total number of unread messages for the authenticated user.
    Useful for notification badges.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        count = Message.objects.filter(
            conversation__in=Conversation.objects.filter(
                db_models.Q(participant_1=user) | db_models.Q(participant_2=user)
            ),
            is_read=False,
        ).exclude(sender=user).count()
        return Response({"unread_count": count})
