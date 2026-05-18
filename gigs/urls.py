from django.urls import path
from .views import (
    CategoryListView,
    GigListView, GigDetailView, GigCreateView,
    GigUpdateDeleteView, MyGigsView,
    CreatePaymentIntentView, SubmitRequirementsView,
    OrderListView, OrderDetailView, ApproveDeliveryView,
    RefundOrderView, StripeWebhookView,
    ExpertSubmitWorkView, CreateReviewView, ExpertReviewListView,
    AdminEarningsView, SellerEarningsView,
)

urlpatterns = [
    # Categories
    path('categories/', CategoryListView.as_view(), name='category-list'),

    # Fixed paths FIRST — before any slug patterns
    path('', GigListView.as_view(), name='gig-list'),
    path('mine/', MyGigsView.as_view(), name='my-gigs'),
    path('create/', GigCreateView.as_view(), name='gig-create'),

    # Earnings
    path('earnings/',    AdminEarningsView.as_view(),  name='admin-earnings'),
    path('my-earnings/', SellerEarningsView.as_view(), name='seller-earnings'),

    # Orders — all fixed paths, must be before <slug>
    path('orders/', OrderListView.as_view(), name='order-list'),
    path('orders/create-payment-intent/', CreatePaymentIntentView.as_view(), name='create-payment-intent'),
    path('orders/<int:order_id>/', OrderDetailView.as_view(), name='order-detail'),
    path('orders/<int:order_id>/requirements/', SubmitRequirementsView.as_view(), name='submit-requirements'),
    path('orders/<int:order_id>/submit/', ExpertSubmitWorkView.as_view(), name='expert-submit-work'),
    path('orders/<int:order_id>/approve/', ApproveDeliveryView.as_view(), name='approve-delivery'),
    path('orders/<int:order_id>/refund/', RefundOrderView.as_view(), name='refund-order'),
    path('orders/<int:order_id>/review/', CreateReviewView.as_view(), name='create-review'),

    # Expert reviews
    path('experts/<int:expert_id>/reviews/', ExpertReviewListView.as_view(), name='expert-reviews'),

    # Stripe webhook
    path('webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),

    # Slug patterns LAST — catch-all, must come after everything fixed
    path('<slug:slug>/', GigDetailView.as_view(), name='gig-detail'),
    path('<slug:slug>/manage/', GigUpdateDeleteView.as_view(), name='gig-manage'),
]