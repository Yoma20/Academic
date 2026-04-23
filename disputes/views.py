import stripe
from django.conf import settings
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError

from gigs.models import Order
from .models import Dispute, DisputeEvidence
from .serializers import DisputeSerializer, DisputeEvidenceSerializer

stripe.api_key = settings.STRIPE_SECRET_KEY


class OpenDisputeView(APIView):
    """
    POST /api/disputes/open/
    Student opens a dispute on an in_progress or submitted order.
    Body: { order_id, reason }
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.user_type != 'student':
            raise PermissionDenied("Only students can open disputes.")

        order_id = request.data.get('order_id')
        reason = request.data.get('reason')

        if not order_id or not reason:
            raise ValidationError({"detail": "order_id and reason are required."})

        try:
            order = Order.objects.select_related(
                'package__gig__expert__user'
            ).get(pk=order_id, student=request.user)
        except Order.DoesNotExist:
            raise ValidationError({"detail": "Order not found."})

        if order.payment_status != 'held':
            return Response(
                {"detail": "Disputes can only be opened on orders with held payments."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if hasattr(order, 'dispute'):
            return Response(
                {"detail": "A dispute already exists for this order."},
                status=status.HTTP_400_BAD_REQUEST
            )

        dispute = Dispute.objects.create(
            order=order,
            opened_by=request.user,
            reason=reason,
        )

        return Response(DisputeSerializer(dispute).data, status=status.HTTP_201_CREATED)


class DisputeDetailView(generics.RetrieveAPIView):
    """GET /api/disputes/<id>/"""
    serializer_class = DisputeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        try:
            dispute = Dispute.objects.select_related(
                'order__student',
                'order__package__gig__expert__user',
            ).prefetch_related('evidence').get(pk=self.kwargs['pk'])
        except Dispute.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Dispute not found.")

        user = self.request.user
        order = dispute.order
        is_student = order.student == user
        is_expert = (
            hasattr(user, 'expert_profile') and
            order.package.gig.expert == user.expert_profile
        )
        if not (is_student or is_expert or user.is_staff):
            raise PermissionDenied("You are not a party to this dispute.")

        return dispute


class SubmitEvidenceView(APIView):
    """
    POST /api/disputes/<id>/evidence/
    Body (multipart): { description, file? }
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            dispute = Dispute.objects.select_related(
                'order__student',
                'order__package__gig__expert__user',
            ).get(pk=pk)
        except Dispute.DoesNotExist:
            return Response(
                {"detail": "Dispute not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if dispute.status not in ('open', 'evidence_submitted'):
            return Response(
                {"detail": "Evidence can only be submitted while the dispute is open."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user
        order = dispute.order
        is_student = order.student == user
        is_expert = (
            hasattr(user, 'expert_profile') and
            order.package.gig.expert == user.expert_profile
        )

        if not (is_student or is_expert):
            raise PermissionDenied("You are not a party to this dispute.")

        if dispute.evidence.filter(submitted_by=user).exists():
            return Response(
                {"detail": "You have already submitted evidence."},
                status=status.HTTP_400_BAD_REQUEST
            )

        description = request.data.get('description', '').strip()
        if not description:
            raise ValidationError({"description": "A written description is required."})

        role = 'student' if is_student else 'expert'
        evidence = DisputeEvidence.objects.create(
            dispute=dispute,
            submitted_by=user,
            submitted_by_role=role,
            description=description,
            file=request.FILES.get('file'),
        )

        dispute.status = 'evidence_submitted'
        dispute.save(update_fields=['status'])

        return Response(
            DisputeEvidenceSerializer(evidence).data,
            status=status.HTTP_201_CREATED
        )


class AdminResolveDisputeView(APIView):
    """
    POST /api/disputes/<id>/resolve/
    Admin only. Body: { decision: 'refund'|'release', resolution_notes }
    """
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        try:
            dispute = Dispute.objects.select_related(
                'order__package__gig__expert',
            ).get(pk=pk)
        except Dispute.DoesNotExist:
            return Response(
                {"detail": "Dispute not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if dispute.status in ('resolved_refund', 'resolved_release', 'closed'):
            return Response(
                {"detail": "This dispute is already resolved."},
                status=status.HTTP_400_BAD_REQUEST
            )

        decision = request.data.get('decision')
        resolution_notes = request.data.get('resolution_notes', '').strip()

        if decision not in ('refund', 'release'):
            raise ValidationError({"decision": "Must be 'refund' or 'release'."})
        if not resolution_notes:
            raise ValidationError({"resolution_notes": "Resolution notes are required."})

        order = dispute.order

        try:
            if decision == 'refund':
                stripe.PaymentIntent.cancel(order.stripe_payment_intent_id)
                order.payment_status = 'refunded'
                order.status = 'archived'
                dispute.status = 'resolved_refund'
            else:
                expert_profile = order.package.gig.expert
                amount_cents = int(order.total_price * 100)
                fee_cents = int(amount_cents * (order.platform_fee_percent / 100))
                transfer_cents = amount_cents - fee_cents

                stripe.PaymentIntent.capture(order.stripe_payment_intent_id)
                transfer = stripe.Transfer.create(
                    amount=transfer_cents,
                    currency="usd",
                    destination=expert_profile.stripe_account_id,
                    metadata={
                        "dispute_id": dispute.id,
                        "resolved_by_admin": True
                    },
                )
                order.stripe_transfer_id = transfer.id
                order.payment_status = 'released'
                order.status = 'completed'
                dispute.status = 'resolved_release'

        except stripe.error.StripeError as e:
            return Response(
                {"detail": f"Stripe error: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY
            )

        dispute.resolution_notes = resolution_notes
        dispute.resolved_by = request.user
        dispute.save()
        order.save()

        return Response(DisputeSerializer(dispute).data)


class DisputeListView(generics.ListAPIView):
    """
    GET /api/disputes/ — admin sees all, students/experts see their own
    """
    serializer_class = DisputeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Dispute.objects.select_related(
            'order__student',
            'order__package__gig__expert__user',
        ).prefetch_related('evidence').order_by('-created_at')

        if user.is_staff:
            status_filter = self.request.query_params.get('status')
            if status_filter:
                qs = qs.filter(status=status_filter)
            return qs

        from django.db.models import Q
        return qs.filter(
            Q(order__student=user) |
            Q(order__package__gig__expert__user=user)
        )