from django.urls import path
from .views import (
    AssignmentListCreateView,
    AssignmentDetailView,
    AssignmentBidListCreateView,
    AssignmentBidDetailView,
    BidListForAssignmentView,
)

urlpatterns = [
    path('', AssignmentListCreateView.as_view(), name='assignment-list'),
    path('<int:pk>/', AssignmentDetailView.as_view(), name='assignment-detail'),
    path('<int:assignment_id>/bids/', BidListForAssignmentView.as_view(), name='bids-for-assignment'),
    path('bids/', AssignmentBidListCreateView.as_view(), name='bid-list'),
    path('bids/<int:pk>/', AssignmentBidDetailView.as_view(), name='bid-detail'),
]
