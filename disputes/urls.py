# disputes/urls.py
from django.urls import path
from .views import (
    OpenDisputeView,
    DisputeDetailView,
    DisputeListView,
    SubmitEvidenceView,
    AdminResolveDisputeView,
)

urlpatterns = [
    path('', DisputeListView.as_view(), name='dispute-list'),
    path('open/', OpenDisputeView.as_view(), name='open-dispute'),
    path('<int:pk>/', DisputeDetailView.as_view(), name='dispute-detail'),
    path('<int:pk>/evidence/', SubmitEvidenceView.as_view(), name='submit-evidence'),
    path('<int:pk>/resolve/', AdminResolveDisputeView.as_view(), name='resolve-dispute'),
]