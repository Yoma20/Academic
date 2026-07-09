from django.urls import path
from .views import (
    CategoryListView,
    GigListView, GigDetailView, GigCreateView,
    GigUpdateDeleteView, MyGigsView,
    CreatePaymentIntentView, ConfirmPaymentView,
    PopularCategoriesView,
    SubmitRequirementsView,
    OrderListView, OrderDetailView,
    ExpertSubmitWorkView,
    ApproveDeliveryView, RefundOrderView,
    CancelOrderView,                          # ← new
    CreateReviewView, ExpertReviewListView,
    AdminEarningsView, SellerEarningsView,
)

urlpatterns = [
    # Categories
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('categories/popular/', PopularCategoriesView.as_view(), name='popular-categories'),

    # Fixed paths FIRST — before any slug patterns
    path('', GigListView.as_view(), name='gig-list'),
    path('mine/', MyGigsView.as_view(), name='my-gigs'),
    path('create/', GigCreateView.as_view(), name='gig-create'),

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
    path('orders/<int:order_id>/cancel/', CancelOrderView.as_view(), name='cancel-order'),  # ← new
    path('orders/<int:order_id>/review/', CreateReviewView.as_view(), name='create-review'),
    path('orders/<int:order_id>/confirm-payment/', ConfirmPaymentView.as_view(), name='confirm-payment'),

    # Expert reviews
    path('experts/<int:expert_id>/reviews/', ExpertReviewListView.as_view(), name='expert-reviews'),

    # Slug-based — must come last
    path('<slug:slug>/', GigDetailView.as_view(), name='gig-detail'),
    path('<slug:slug>/manage/', GigUpdateDeleteView.as_view(), name='gig-manage'),
]