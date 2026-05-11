from django.contrib.auth import get_user_model
from django.db import models as db_models
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

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
            .select_related("participant_1", "participant_2", "gig")
            .prefetch_related("messages", "offers")
            .order_by("-updated_at")
        )


class StartConversationView(APIView):
    """
    POST /api/messaging/conversations/start/
    Body: { recipient_id, initial_message?, gig_id? }
    Creates or retrieves a conversation and optionally sends the first message.
    """
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

        conversation, created = Conversation.objects.get_or_create(
            participant_1=p1, participant_2=p2
        )

        # Attach gig context if provided and not already set
        if gig_id and not conversation.gig_id:
            try:
                from gigs.models import Gig
                conversation.gig = Gig.objects.get(pk=gig_id)
                conversation.save()
            except Exception:
                pass

        if initial_message:
            Message.objects.create(
                conversation=conversation,
                sender=user,
                content=initial_message,
            )
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

        Message.objects.filter(
            conversation=conversation, is_read=False
        ).exclude(sender=user).update(is_read=True)

        return (
            Message.objects.filter(conversation=conversation)
            .select_related("sender", "offer", "offer__sender")
        )


class SendMessageView(APIView):
    """
    POST /api/messaging/conversations/<conv_id>/send/
    Body: { content }
    Sends a plain text message in an existing conversation.
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
            message_type="text",
        )
        conversation.save()

        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)


class SendOfferView(APIView):
    """
    POST /api/messaging/conversations/<conv_id>/offer/
    Only experts can send offers. Creates an Offer + a linked offer-type Message.
    Body: { title, description?, price, delivery_days, revision_number, package_id?, parent_offer_id? }
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, conv_id):
        # Only experts can send offers
        if request.user.user_type != "expert":
            return Response(
                {"detail": "Only experts can send offers."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            conversation = Conversation.objects.get(pk=conv_id)
        except Conversation.DoesNotExist:
            return Response({"detail": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)

        if conversation.participant_1 != request.user and conversation.participant_2 != request.user:
            return Response({"detail": "Not a participant."}, status=status.HTTP_403_FORBIDDEN)

        serializer = SendOfferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Resolve optional package
        package = None
        if data.get("package_id"):
            try:
                from gigs.models import GigPackage
                package = GigPackage.objects.get(pk=data["package_id"])
            except Exception:
                return Response({"detail": "Package not found."}, status=status.HTTP_400_BAD_REQUEST)

        # Resolve optional parent offer (counter-offer scenario)
        parent_offer = None
        if data.get("parent_offer_id"):
            try:
                parent_offer = Offer.objects.get(pk=data["parent_offer_id"], conversation=conversation)
                # Mark parent as countered
                parent_offer.status = Offer.STATUS_COUNTERED
                parent_offer.save(update_fields=["status"])
            except Offer.DoesNotExist:
                pass

        # Expire any other pending offers in this conversation from this sender
        Offer.objects.filter(
            conversation=conversation,
            sender=request.user,
            status=Offer.STATUS_PENDING,
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

        # Create the linked message so it appears in the chat thread
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
                "message": MessageSerializer(message).data,
                "offer": OfferSerializer(offer).data,
            },
            status=status.HTTP_201_CREATED,
        )


class RespondOfferView(APIView):
    """
    POST /api/messaging/offers/<offer_id>/respond/
    Buyer accepts or declines an offer.
    Body: { action: "accept" | "decline" }

    On accept: creates a pending Order and triggers payment-intent creation.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, offer_id):
        try:
            offer = Offer.objects.select_related("conversation", "sender", "package").get(pk=offer_id)
        except Offer.DoesNotExist:
            return Response({"detail": "Offer not found."}, status=status.HTTP_404_NOT_FOUND)

        conversation = offer.conversation

        # Must be the OTHER participant (i.e. the buyer)
        if offer.sender == request.user:
            return Response({"detail": "You cannot respond to your own offer."}, status=status.HTTP_403_FORBIDDEN)
        if conversation.participant_1 != request.user and conversation.participant_2 != request.user:
            return Response({"detail": "Not a participant."}, status=status.HTTP_403_FORBIDDEN)

        if offer.status != Offer.STATUS_PENDING:
            return Response(
                {"detail": f"Offer is already {offer.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RespondOfferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data["action"]

        if action == "decline":
            offer.status = Offer.STATUS_DECLINED
            offer.save(update_fields=["status"])
            # Post a system-style text message in chat
            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content="Offer declined.",
                message_type="text",
            )
            conversation.save()
            return Response(OfferSerializer(offer).data)

        # ── Accept flow ──────────────────────────────────────────────────────
        # Validate expert has Stripe set up before creating order
        expert = offer.sender
        try:
            expert_profile = expert.expert_profile
            if not expert_profile.stripe_account_id or not expert_profile.stripe_account_verified:
                return Response(
                    {"detail": "This expert has not set up their payout account yet."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception:
            return Response(
                {"detail": "Expert profile not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create Order matching the Order model in gigs/models.py
        try:
            from gigs.models import Order
            order = Order.objects.create(
                student=request.user,
                package=offer.package,
                package_price=offer.price,
                extras_price=0,
                total_price=offer.price,
                status="pending",
                payment_status="unpaid",
            )
            offer.status = Offer.STATUS_ACCEPTED
            offer.order = order
            offer.save(update_fields=["status", "order"])
        except Exception as e:
            return Response(
                {"detail": f"Could not create order: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Create Stripe PaymentIntent
        try:
            import stripe
            from django.conf import settings as django_settings
            stripe.api_key = django_settings.STRIPE_SECRET_KEY

            amount_cents = int(offer.price * 100)
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency="usd",
                transfer_data={"destination": expert_profile.stripe_account_id},
                application_fee_amount=int(amount_cents * 0.10),  # 10% platform fee
                metadata={"order_id": order.id, "offer_id": offer.id},
            )
            order.stripe_payment_intent_id = intent["id"]
            order.save(update_fields=["stripe_payment_intent_id"])

            client_secret = intent["client_secret"]
        except Exception as e:
            return Response(
                {"detail": f"Payment setup failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Post confirmation message in chat
        Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content="Offer accepted! Proceeding to payment.",
            message_type="text",
        )
        conversation.save()

        return Response(
            {
                "offer": OfferSerializer(offer).data,
                "order_id": order.id,
                "client_secret": client_secret,
            },
            status=status.HTTP_200_OK,
        )


class UnreadCountView(APIView):
    """
    GET /api/messaging/unread-count/
    Returns the total number of unread messages for the authenticated user.
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