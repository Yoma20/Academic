import stripe
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import AcademicCategory, Gig, GigPackage, GigExtra, Order, OrderRequirements, Review
from .serializers import (
    AcademicCategorySerializer, GigSerializer, GigWriteSerializer,
    OrderSerializer, OrderRequirementsSerializer, ReviewSerializer,
)

stripe.api_key = settings.STRIPE_SECRET_KEY


# ─── Category views ───────────────────────────────────────────────────────────

class CategoryListView(generics.ListAPIView):
    """GET /api/gigs/categories/ — returns full category tree (parents + children)"""
    serializer_class = AcademicCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = AcademicCategory.objects.filter(parent=None).prefetch_related('subcategories')


# ─── Gig views ────────────────────────────────────────────────────────────────

class GigListView(generics.ListAPIView):
    """
    GET /api/gigs/
    Supports: ?category=<id>, ?search=<str>, ?min=<price>, ?max=<price>, ?sort=sales|created_at
    """
    serializer_class = GigSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Gig.objects.filter(is_active=True).prefetch_related('packages', 'extras')
        params = self.request.query_params

        if cat := params.get('category'):
            qs = qs.filter(Q(category__id=cat) | Q(category__parent__id=cat))
        if search := params.get('search'):
            qs = qs.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(short_title__icontains=search)
            )
        if min_price := params.get('min'):
            qs = qs.filter(packages__price__gte=min_price)
        if max_price := params.get('max'):
            qs = qs.filter(packages__price__lte=max_price)

        sort = params.get('sort', 'sales')
        if sort == 'sales':
            qs = qs.order_by('-sales')
        else:
            qs = qs.order_by('-created_at')

        return qs.distinct()


class GigDetailView(generics.RetrieveAPIView):
    """GET /api/gigs/<id>/"""
    serializer_class = GigSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'slug'
    queryset = Gig.objects.prefetch_related('packages', 'extras')


class GigCreateView(APIView):
    """POST /api/gigs/ — experts only"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.user_type != 'expert':
            raise PermissionDenied("Only experts can create gigs.")
        if not hasattr(request.user, 'expert_profile'):
            raise PermissionDenied("Complete your expert profile first.")

        existing_count = Gig.objects.filter(expert=request.user.expert_profile).count()
        if existing_count >= 3:
            return Response(
                {"detail": "You have reached the maximum of 3 gigs. Delete an existing gig to create a new one."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = GigWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        gig = serializer.save(expert=request.user.expert_profile)
        return Response(GigSerializer(gig).data, status=status.HTTP_201_CREATED)


class GigUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /api/gigs/<id>/manage/ — owner expert only"""
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return GigWriteSerializer
        return GigSerializer

    def get_queryset(self):
        return Gig.objects.filter(expert=self.request.user.expert_profile)

    def get_object(self):
        if not hasattr(self.request.user, 'expert_profile'):
            raise PermissionDenied("Only experts can manage gigs.")
        return super().get_object()


class MyGigsView(generics.ListAPIView):
    """GET /api/gigs/mine/ — expert's own gigs"""
    serializer_class = GigSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if not hasattr(self.request.user, 'expert_profile'):
            return Gig.objects.none()
        return Gig.objects.filter(
            expert=self.request.user.expert_profile
        ).prefetch_related('packages', 'extras').order_by('-created_at')


# ─── Order views ──────────────────────────────────────────────────────────────

class CreatePaymentIntentView(APIView):
    """
    POST /api/gigs/orders/create-payment-intent/
    Body: { package_id, extra_ids?: [] }
    Creates Stripe PaymentIntent and an Order in 'pending' state.
    Returns: { client_secret, order_id, total_price }
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.user_type != 'student':
            raise PermissionDenied("Only students can place orders.")

        package_id = request.data.get('package_id')
        extra_ids = request.data.get('extra_ids', [])

        if not package_id:
            raise ValidationError({"package_id": "This field is required."})

        try:
            package = GigPackage.objects.select_related(
                'gig__expert'
            ).get(pk=package_id)
        except GigPackage.DoesNotExist:
            raise ValidationError({"package_id": "Package not found."})

        expert_profile = package.gig.expert
        if not expert_profile.stripe_account_id or not expert_profile.stripe_account_verified:
            return Response(
                {"detail": "This expert has not set up their payout account yet."},
                status=status.HTTP_400_BAD_REQUEST
            )

        extras = GigExtra.objects.filter(pk__in=extra_ids, gig=package.gig)
        extras_price = sum(e.price for e in extras)
        total_price = package.price + extras_price
        amount_cents = int(total_price * 100)

        extra_days = sum(e.extra_days for e in extras)
        deadline = timezone.now() + timedelta(
            days=package.delivery_days + extra_days
        )

        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency="usd",
            capture_method="manual",
            metadata={
                "package_id": package.id,
                "student_id": request.user.id,
                "expert_id": expert_profile.id,
            }
        )

        order = Order.objects.create(
            student=request.user,
            package=package,
            package_price=package.price,
            extras_price=extras_price,
            total_price=total_price,
            deadline=deadline,
            stripe_payment_intent_id=intent.id,
            payment_status='held',
            status='pending',
        )
        order.extras.set(extras)

        return Response({
            "client_secret": intent.client_secret,
            "order_id": order.id,
            "total_price": str(total_price),
        }, status=status.HTTP_201_CREATED)


class SubmitRequirementsView(APIView):
    """
    POST /api/gigs/orders/<order_id>/requirements/
    Student submits requirements — moves order to 'in_progress'.
    Body (multipart): { citation_style, word_count, additional_notes, answers, rubric_file? }
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        try:
            order = Order.objects.get(pk=order_id, student=request.user)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        if order.status != 'pending':
            return Response(
                {"detail": "Requirements already submitted."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if hasattr(order, 'requirements'):
            return Response(
                {"detail": "Requirements already submitted."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = OrderRequirementsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(order=order, rubric_file=request.FILES.get('rubric_file'))

        order.status = 'in_progress'
        order.save(update_fields=['status'])

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class OrderListView(generics.ListAPIView):
    """
    GET /api/gigs/orders/
    Students see their orders. Experts see orders for their gigs.
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'student':
            return Order.objects.filter(student=user).select_related(
                'package__gig__expert__user'
            ).prefetch_related('extras', 'requirements').order_by('-created_at')
        elif user.user_type == 'expert' and hasattr(user, 'expert_profile'):
            return Order.objects.filter(
                package__gig__expert=user.expert_profile
            ).select_related(
                'package__gig', 'student'
            ).prefetch_related('extras', 'requirements').order_by('-created_at')
        return Order.objects.none()


class ApproveDeliveryView(APIView):
    """
    POST /api/gigs/orders/<order_id>/approve/
    Student approves delivery — captures payment and transfers to expert.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        try:
            order = Order.objects.select_related(
                'package__gig__expert'
            ).get(pk=order_id, student=request.user)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        if order.payment_status != 'held':
            return Response(
                {"detail": "No held payment for this order."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if order.status != 'submitted':
            return Response(
                {"detail": "Expert has not submitted the work yet."},
                status=status.HTTP_400_BAD_REQUEST
            )

        expert_profile = order.package.gig.expert
        amount_cents = int(order.total_price * 100)
        fee_cents = int(amount_cents * (order.platform_fee_percent / 100))
        transfer_cents = amount_cents - fee_cents

        try:
            stripe.PaymentIntent.capture(order.stripe_payment_intent_id)
            transfer = stripe.Transfer.create(
                amount=transfer_cents,
                currency="usd",
                destination=expert_profile.stripe_account_id,
                metadata={"order_id": order.id},
            )
        except stripe.error.StripeError as e:
            return Response({"detail": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        order.payment_status = 'released'
        order.status = 'completed'
        order.stripe_transfer_id = transfer.id
        order.save()

        # Bump gig sales count
        order.package.gig.sales = order.package.gig.sales + 1
        order.package.gig.save(update_fields=['sales'])

        return Response({"detail": "Delivery approved. Payment released."})


class RefundOrderView(APIView):
    """
    POST /api/gigs/orders/<order_id>/refund/
    Cancels uncaptured PaymentIntent and archives the order.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        try:
            order = Order.objects.get(pk=order_id, student=request.user)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        if order.payment_status != 'held':
            return Response(
                {"detail": "No held payment to refund."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            stripe.PaymentIntent.cancel(order.stripe_payment_intent_id)
        except stripe.error.StripeError as e:
            return Response({"detail": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        order.payment_status = 'refunded'
        order.status = 'archived'
        order.save()
        return Response({"detail": "Order refunded."})


class StripeWebhookView(APIView):
    """POST /api/gigs/webhook/ — Stripe async event handler"""
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        payload = request.body
        sig = request.META.get("HTTP_STRIPE_SIGNATURE", "")
        try:
            event = stripe.Webhook.construct_event(
                payload, sig, settings.STRIPE_WEBHOOK_SECRET
            )
        except (ValueError, stripe.error.SignatureVerificationError):
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if event['type'] == 'payment_intent.payment_failed':
            intent_id = event['data']['object']['id']
            Order.objects.filter(
                stripe_payment_intent_id=intent_id,
                payment_status='held'
            ).update(payment_status='unpaid', status='archived')

        return Response({"detail": "ok"})
    
class ExpertSubmitWorkView(APIView):
    """
    POST /api/gigs/orders/<order_id>/submit/
    Expert marks work as submitted. Moves order to 'submitted'.
    Student can then approve or dispute.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        if request.user.user_type != 'expert':
            raise PermissionDenied("Only experts can submit work.")

        if not hasattr(request.user, 'expert_profile'):
            raise PermissionDenied("Expert profile not found.")

        try:
            order = Order.objects.select_related(
                'package__gig__expert'
            ).get(pk=order_id)
        except Order.DoesNotExist:
            return Response(
                {"detail": "Order not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verify this expert owns the gig
        if order.package.gig.expert != request.user.expert_profile:
            raise PermissionDenied("This is not your order.")

        if order.status != 'in_progress':
            return Response(
                {"detail": f"Order is '{order.status}' — can only submit from 'in_progress'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not hasattr(order, 'requirements'):
            return Response(
                {"detail": "Student has not submitted requirements yet."},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.status = 'submitted'
        order.save(update_fields=['status'])

        return Response({"detail": "Work submitted. Awaiting student approval."})


class CreateReviewView(APIView):
    """
    POST /api/gigs/orders/<order_id>/review/
    Student leaves a multi-dimensional review after order completes.
    Body: { rubric_adherence_score, timeliness_score, communication_score, comment, would_recommend }
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        if request.user.user_type != 'student':
            raise PermissionDenied("Only students can leave reviews.")

        try:
            order = Order.objects.select_related(
                'package__gig__expert'
            ).get(pk=order_id, student=request.user)
        except Order.DoesNotExist:
            return Response(
                {"detail": "Order not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if order.status != 'completed':
            return Response(
                {"detail": "You can only review a completed order."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if hasattr(order, 'review'):
            return Response(
                {"detail": "You have already reviewed this order."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            order=order,
            student=request.user,
            expert=order.package.gig.expert,
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ExpertReviewListView(generics.ListAPIView):
    """
    GET /api/gigs/experts/<expert_id>/reviews/
    Public — anyone can see an expert's reviews.
    """
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Review.objects.filter(
            expert__id=self.kwargs['expert_id']
        ).select_related(
            'student', 'expert__user', 'order__package__gig'
        ).order_by('-created_at')


class OrderDetailView(generics.RetrieveAPIView):
    """
    GET /api/gigs/orders/<order_id>/
    Student or expert can view a single order.
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        user = self.request.user
        try:
            order = Order.objects.select_related(
                'package__gig__expert__user', 'student'
            ).prefetch_related('extras', 'requirements').get(
                pk=self.kwargs['order_id']
            )
        except Order.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Order not found.")

        is_student = order.student == user
        is_expert = (
            hasattr(user, 'expert_profile') and
            order.package.gig.expert == user.expert_profile
        )
        if not (is_student or is_expert):
            raise PermissionDenied("You are not party to this order.")

        return order