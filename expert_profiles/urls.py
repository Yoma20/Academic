from django.urls import path
from .views import ExpertProfileList, ExpertProfileDetail

urlpatterns = [
    path('', ExpertProfileList.as_view(), name='expert-profile-list'),
    path('<int:pk>/', ExpertProfileDetail.as_view(), name='expert-profile-detail'),
]
