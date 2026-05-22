from collections import defaultdict
from datetime import timedelta

from django.core.cache import cache
from django.db.models import Q, Sum
from django.utils import timezone

from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import IsAdminUser
from .models import (
    AcademicCategory, Gig, GigPackage, GigExtra,
    Order, OrderRequirements, Review,
)
from .serializers import (
    AcademicCategorySerializer,
    GigSerializer, GigWriteSerializer,
    OrderSerializer, OrderRequirementsSerializer,
    ReviewSerializer,
)


# ─── Categories ───────────────────────────────────────────────────────────────

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
    """GET /api/gigs/<slug>/"""
    serializer_class = GigSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'slug'
    queryset = Gig.objects.prefetch_related('packages', 'extras')


class GigCreateView(APIView):
    """POST /api/gigs/create/ — experts only"""
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
    """GET/PATCH/DELETE /api/gigs/<slug>/manage/ — owner expert only"""
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'slug'

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
    pagination_class = None

    def get_queryset(self):
        if not hasattr(self.request.user, 'expert_profile'):
            return Gig.objects.none()
        return Gig.objects.filter(
            expert=self.request.user.expert_profile
        ).prefetch_related('packages', 'extras').order_by('-created_at')


# ─── Orders ───────────────────────────────────────────────────────────────────

class CreatePaymentIntentView(APIView):
    """
    POST /api/gigs/orders/create-payment-intent/
    Body: { package_id, extra_ids?: [] }
    Creates an Order in 'pending' state and returns order_id + total_price.
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
            package = GigPackage.objects.select_related('gig__expert').get(pk=package_id)
        except GigPackage.DoesNotExist:
            raise ValidationError({"package_id": "Package not found."})

        extras = GigExtra.objects.filter(pk__in=extra_ids, gig=package.gig)
        extras_price = sum(e.price for e in extras)
        total_price = package.price + extras_price

        extra_days = sum(e.extra_days for e in extras)
        deadline = timezone.now() + timedelta(days=package.delivery_days + extra_days)

        order = Order.objects.create(
            student=request.user,
            package=package,
            package_price=package.price,
            extras_price=extras_price,
            total_price=total_price,
            deadline=deadline,
            payment_status='unpaid',
            status='pending',
        )
        order.extras.set(extras)

        return Response({
            'order_id': order.id,
            'amount': str(total_price),
        }, status=status.HTTP_201_CREATED)


class ConfirmPaymentView(APIView):
    """
    POST /api/gigs/orders/<order_id>/confirm-payment/
    Called by the frontend after:
      - PayPal payment approved
      - Student submits bank transfer notification

    Body: { method: "paypal" | "bank_transfer", paypal_order_id?: string, pay_token?: string }

    PayPal       → sets payment_status = "held", status = "in_progress"
    Bank transfer → sets payment_status = "unpaid", status = "pending"
                    (admin manually confirms receipt and updates later)
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, student=request.user)
        except Order.DoesNotExist:
            return Response({'detail': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

        method = request.data.get('method')

        if method == 'paypal':
            order.payment_status = 'held'
            order.status = 'in_progress'
            order.save(update_fields=['payment_status', 'status'])
        elif method == 'bank_transfer':
            order.payment_status = 'unpaid'
            order.status = 'pending'
            order.save(update_fields=['payment_status', 'status'])
        else:
            return Response({'detail': 'Invalid payment method.'}, status=status.HTTP_400_BAD_REQUEST)

        # Delete the one-time pay token now that payment has been confirmed
        pay_token = request.data.get('pay_token', '').strip()
        if pay_token:
            cache.delete(f'pay_token:{pay_token}')

        return Response({'detail': 'Payment confirmed.'})


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
    pagination_class = None

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


class OrderDetailView(generics.RetrieveAPIView):
    """GET /api/gigs/orders/<order_id>/"""
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
            order.package is not None and
            order.package.gig.expert == user.expert_profile
        )
        if not (is_student or is_expert or user.is_staff):
            raise PermissionDenied("You are not party to this order.")

        return order


class ExpertSubmitWorkView(APIView):
    """
    POST /api/gigs/orders/<order_id>/submit/
    Expert marks work as submitted. Moves order to 'submitted'.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        try:
            order = Order.objects.select_related(
                'package__gig__expert__user'
            ).get(id=order_id)
        except Order.DoesNotExist:
            return Response({'detail': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

        if order.package.gig.expert.user != request.user:
            return Response({'detail': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)

        if order.status != 'in_progress':
            return Response(
                {'detail': 'Order must be in-progress before submitting work.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.status = 'submitted'
        order.save(update_fields=['status'])
        return Response(OrderSerializer(order).data)


class ApproveDeliveryView(APIView):
    """
    POST /api/gigs/orders/<order_id>/approve/
    Student approves delivery — marks payment as released and order as completed.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        try:
            order = Order.objects.select_related(
                'package__gig__expert'
            ).get(pk=order_id, student=request.user)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        if order.status != 'submitted':
            return Response(
                {"detail": "Expert has not submitted the work yet."},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.payment_status = 'released'
        order.status = 'completed'
        order.save(update_fields=['payment_status', 'status'])

        # Bump gig sales count
        try:
            order.package.gig.sales += 1
            order.package.gig.save(update_fields=['sales'])
        except Exception:
            pass

        return Response({"detail": "Delivery approved. Payment released."})


class RefundOrderView(APIView):
    """
    POST /api/gigs/orders/<order_id>/refund/
    Archives the order and marks it refunded. Admin handles actual money return.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, student=request.user)
        except Order.DoesNotExist:
            return Response({'detail': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

        if order.payment_status not in ('held', 'released'):
            return Response(
                {'detail': 'Order cannot be refunded.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.payment_status = 'refunded'
        order.status = 'archived'
        order.save(update_fields=['payment_status', 'status'])
        return Response(OrderSerializer(order).data)


# ─── Reviews ──────────────────────────────────────────────────────────────────

class CreateReviewView(APIView):
    """
    POST /api/gigs/orders/<order_id>/review/
    Student leaves a review after order completes.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        try:
            order = Order.objects.select_related(
                'package__gig__expert', 'student'
            ).get(id=order_id, student=request.user)
        except Order.DoesNotExist:
            return Response({'detail': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

        if order.status != 'completed':
            return Response(
                {'detail': 'You can only review a completed order.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if hasattr(order, 'review'):
            return Response(
                {'detail': 'You have already reviewed this order.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            order=order,
            student=request.user,
            expert=order.package.gig.expert,
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ExpertReviewListView(APIView):
    """GET /api/gigs/experts/<expert_id>/reviews/ — public"""
    permission_classes = [permissions.AllowAny]

    def get(self, request, expert_id):
        reviews = Review.objects.filter(expert_id=expert_id).select_related(
            'student', 'order__package__gig'
        ).order_by('-created_at')
        return Response(ReviewSerializer(reviews, many=True).data)


# ─── Earnings ─────────────────────────────────────────────────────────────────

class AdminEarningsView(APIView):
    """
    GET /api/gigs/earnings/?from=YYYY-MM-DD&to=YYYY-MM-DD
    Admin only. Returns per-expert earnings summary for a date range.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        today      = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_end   = week_start + timedelta(days=6)

        from_date = request.query_params.get('from', str(week_start))
        to_date   = request.query_params.get('to',   str(week_end))

        orders = (
            Order.objects
            .filter(
                status='completed',
                payment_status='released',
                updated_at__date__range=[from_date, to_date],
            )
            .select_related('package__gig__expert', 'package__gig__expert__user')
        )

        earnings = defaultdict(lambda: {
            'username': '',
            'email':    '',
            'orders':   0,
            'total':    0.0,
        })

        for order in orders:
            try:
                expert_user = order.package.gig.expert.user
            except Exception:
                continue
            earnings[expert_user.id]['username'] = expert_user.username
            earnings[expert_user.id]['email']    = expert_user.email
            earnings[expert_user.id]['orders']  += 1
            earnings[expert_user.id]['total']   += float(order.total_price)

        return Response({
            'period':  {'from': str(from_date), 'to': str(to_date)},
            'experts': list(earnings.values()),
        })


class SellerEarningsView(APIView):
    """
    GET /api/gigs/my-earnings/?period=week|month|all
    Expert's own earnings summary.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.user_type != 'expert':
            return Response(
                {'detail': 'Only experts have earnings.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        period = request.query_params.get('period', 'month')
        today  = timezone.now().date()

        if period == 'week':
            from_date = today - timedelta(days=today.weekday())
        elif period == 'month':
            from_date = today.replace(day=1)
        else:
            from_date = None

        qs = Order.objects.filter(
            package__gig__expert__user=user,
            status='completed',
            payment_status='released',
        ).select_related('package__gig', 'student')

        if from_date:
            qs = qs.filter(updated_at__date__gte=from_date)

        orders_data = []
        for order in qs.order_by('-updated_at'):
            try:
                gig_title = order.package.gig.title
            except Exception:
                gig_title = None
            orders_data.append({
                'id':               order.id,
                'gig_title':        gig_title,
                'student_username': order.student.username,
                'total_price':      str(order.total_price),
                'payment_status':   order.payment_status,
                'status':           order.status,
                'updated_at':       order.updated_at,
            })

        gross = sum(float(o['total_price']) for o in orders_data)
        fee   = gross * 0.10
        net   = gross - fee

        pending_qs = Order.objects.filter(
            package__gig__expert__user=user,
            status='completed',
            payment_status='held',
        )
        if from_date:
            pending_qs = pending_qs.filter(updated_at__date__gte=from_date)
        pending_gross = float(pending_qs.aggregate(t=Sum('total_price'))['t'] or 0)
        pending_net   = pending_gross * 0.90

        return Response({
            'period': period,
            'summary': {
                'gross':            round(gross, 2),
                'fee':              round(fee, 2),
                'net':              round(net, 2),
                'pending':          round(pending_net, 2),
                'completed_orders': len(orders_data),
            },
            'orders': orders_data,
        })