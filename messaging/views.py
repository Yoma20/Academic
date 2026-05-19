from django.contrib.auth import get_user_model
from django.db import models as db_models
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
import secrets
from django.core.cache import cache

from .models import Conversation, Message, Offer
from .serializers import (
    ConversationSerializer,
    MessageSerializer,
    OfferSerializer,
    StartConversationSerializer,
    SendOfferSerializer,
    RespondOfferSerializer,
)

User = get_user_model()

ALLOWED_MIME_TYPES = {
    # Images
    "image/jpeg", "image/png", "image/gif", "image/webp",
    # Video
    "video/mp4", "video/webm", "video/quicktime",
    # Documents
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/plain",
    "application/zip",
}
MAX_FILE_SIZE_MB = 20


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
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        return (
            Conversation.objects.filter(
                db_models.Q(participant_1=user) | db_models.Q(participant_2=user)
            )
            .select_related("participant_1", "participant_2", "participant_1__expert_profile", "participant_2__expert_profile", "gig")
            .prefetch_related("messages", "offers")
            .order_by("-updated_at")
        )


class StartConversationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = StartConversationSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        recipient_id = serializer.validated_data["recipient_id"]
        initial_message = serializer.validated_data.get("initial_message", "").strip()
        gig_id = serializer.validated_data.get("gig_id")
        recipient = User.objects.get(pk=recipient_id)
        user = request.user

        p1, p2 = (user, recipient) if user.id < recipient.id else (recipient, user)
        conversation, created = Conversation.objects.get_or_create(participant_1=p1, participant_2=p2)

        if gig_id and not conversation.gig_id:
            try:
                from gigs.models import Gig
                gig = Gig.objects.get(pk=gig_id, is_active=True)
                other = recipient if user != recipient else user
                if gig.expert.user != other:
                    return Response({"detail": "Gig does not belong to this expert."}, status=status.HTTP_400_BAD_REQUEST)
                conversation.gig = gig
                conversation.save()
            except Gig.DoesNotExist:
                return Response({"detail": "Invalid or inactive gig."}, status=status.HTTP_400_BAD_REQUEST)

        if initial_message:
            Message.objects.create(conversation=conversation, sender=user, content=initial_message)
            conversation.save()

        out = ConversationSerializer(conversation, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class MessageListView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated, IsConversationParticipant]
    pagination_class = None

    def get_queryset(self):
        conv_id = self.kwargs["conv_id"]
        user = self.request.user
        try:
            conversation = Conversation.objects.get(pk=conv_id)
        except Conversation.DoesNotExist:
            return Message.objects.none()
        self.check_object_permissions(self.request, conversation)
        Message.objects.filter(conversation=conversation, is_read=False).exclude(sender=user).update(is_read=True)
        return Message.objects.filter(conversation=conversation).select_related(
            "sender", "sender__expert_profile", "offer", "offer__sender"
        )


class SendMessageView(APIView):
    """
    POST /api/messaging/conversations/<conv_id>/send/
    Body (JSON):      { content }
    Body (multipart): { content?, files[] }

    At least one of content or files must be present.
    Each file is saved as a separate Message with message_type="file".
    Text message is created first (if present), then one message per file.
    Returns a single message object, or a list when multiple messages are created.
    """
    permission_classes = [permissions.IsAuthenticated, IsConversationParticipant]

    def post(self, request, conv_id):
        try:
            conversation = Conversation.objects.get(pk=conv_id)
        except Conversation.DoesNotExist:
            return Response({"detail": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, conversation)

        content = request.data.get("content", "").strip()
        files = request.FILES.getlist("files")

        if not content and not files:
            return Response({"detail": "Message content cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)

        if content and len(content) > 5000:
            return Response({"detail": "Message too long (max 5000 characters)."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate all files before creating anything
        for f in files:
            if f.content_type not in ALLOWED_MIME_TYPES:
                return Response(
                    {"detail": f"File type '{f.content_type}' is not allowed."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if f.size > MAX_FILE_SIZE_MB * 1024 * 1024:
                return Response(
                    {"detail": f"'{f.name}' exceeds the {MAX_FILE_SIZE_MB} MB limit."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        created_messages = []

        if content:
            created_messages.append(Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content=content,
                message_type="text",
            ))

        for f in files:
            created_messages.append(Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content="",
                message_type="file",
                file=f,
                file_name=f.name,
            ))

        conversation.save()  # bumps updated_at

        serialized = MessageSerializer(created_messages, many=True, context={"request": request}).data
        if len(serialized) == 1:
            return Response(serialized[0], status=status.HTTP_201_CREATED)
        return Response(serialized, status=status.HTTP_201_CREATED)


class SendOfferView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, conv_id):
        if request.user.user_type != "expert":
            return Response({"detail": "Only experts can send offers."}, status=status.HTTP_403_FORBIDDEN)

        try:
            conversation = Conversation.objects.get(pk=conv_id)
        except Conversation.DoesNotExist:
            return Response({"detail": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)

        if conversation.participant_1 != request.user and conversation.participant_2 != request.user:
            return Response({"detail": "Not a participant."}, status=status.HTTP_403_FORBIDDEN)

        serializer = SendOfferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        package = None
        if data.get("package_id"):
            try:
                from gigs.models import GigPackage
                package = GigPackage.objects.get(pk=data["package_id"])
            except Exception:
                return Response({"detail": "Package not found."}, status=status.HTTP_400_BAD_REQUEST)

        parent_offer = None
        if data.get("parent_offer_id"):
            try:
                parent_offer = Offer.objects.get(pk=data["parent_offer_id"], conversation=conversation)
                parent_offer.status = Offer.STATUS_COUNTERED
                parent_offer.save(update_fields=["status"])
            except Offer.DoesNotExist:
                pass

        Offer.objects.filter(
            conversation=conversation, sender=request.user, status=Offer.STATUS_PENDING,
        ).update(status=Offer.STATUS_EXPIRED)

        offer = Offer.objects.create(
            conversation=conversation,
            sender=request.user,
            package=package,
            title=data["title"],
            description=data.get("description", ""),
            price=data["price"],
            delivery_days=data["delivery_days"],
            revision_number=data["revision_number"],
            parent_offer=parent_offer,
            expires_at=timezone.now() + timezone.timedelta(days=7),
        )

        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=f"Custom offer: {offer.title} — ${offer.price}",
            message_type="offer",
            offer=offer,
        )
        conversation.save()

        return Response(
            {
                "message": MessageSerializer(message, context={"request": request}).data,
                "offer": OfferSerializer(offer, context={"request": request}).data,
            },
            status=status.HTTP_201_CREATED,
        )


class RespondOfferView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, offer_id):
        try:
            offer = Offer.objects.select_related("conversation", "sender", "package").get(pk=offer_id)
        except Offer.DoesNotExist:
            return Response({"detail": "Offer not found."}, status=status.HTTP_404_NOT_FOUND)

        conversation = offer.conversation

        if offer.sender == request.user:
            return Response({"detail": "You cannot respond to your own offer."}, status=status.HTTP_403_FORBIDDEN)
        if conversation.participant_1 != request.user and conversation.participant_2 != request.user:
            return Response({"detail": "Not a participant."}, status=status.HTTP_403_FORBIDDEN)
        if offer.status != Offer.STATUS_PENDING:
            return Response({"detail": f"Offer is already {offer.status}."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = RespondOfferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data["action"]

        if action == "decline":
            offer.status = Offer.STATUS_DECLINED
            offer.save(update_fields=["status"])
            Message.objects.create(conversation=conversation, sender=request.user, content="Offer declined.", message_type="text")
            conversation.save()
            return Response(OfferSerializer(offer).data)

        try:
            from gigs.models import Order
            from datetime import timedelta
            order = Order.objects.create(
                student=request.user,
                package=offer.package,
                package_price=offer.price,
                extras_price=0,
                total_price=offer.price,
                status="pending",
                payment_status="unpaid",
                deadline=timezone.now() + timedelta(days=offer.delivery_days),
            )
            offer.status = Offer.STATUS_ACCEPTED
            offer.order = order
            offer.save(update_fields=["status", "order"])
        except Exception as e:
            return Response({"detail": f"Could not create order: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        Message.objects.create(
            conversation=conversation, sender=request.user,
            content="Offer accepted! Proceeding to payment.", message_type="text",
        )
        conversation.save()

        pay_token = secrets.token_urlsafe(32)
        cache.set(f"pay_token:{pay_token}", {
            "order_id": order.id,
            "amount": str(offer.price),
            "user_id": request.user.id,
        }, timeout=900)

        return Response({"offer": OfferSerializer(offer).data, "pay_token": pay_token}, status=status.HTTP_200_OK)


class RedeemPayTokenView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        token = request.data.get("token", "").strip()
        if not token:
            return Response({"detail": "Token required."}, status=status.HTTP_400_BAD_REQUEST)
        data = cache.get(f"pay_token:{token}")
        if not data:
            return Response({"detail": "Token expired or invalid."}, status=status.HTTP_400_BAD_REQUEST)
        if data["user_id"] != request.user.id:
            return Response({"detail": "Unauthorized."}, status=status.HTTP_403_FORBIDDEN)
        return Response({"order_id": data["order_id"], "amount": data["amount"]})


class UnreadCountView(APIView):
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