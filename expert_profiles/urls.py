from django.urls import path
from .views import ExpertProfileList, ExpertProfileDetail, ExpertProfileMe

urlpatterns = [
    path('',          ExpertProfileList.as_view(),   name='expert-profile-list'),
    path('me/',       ExpertProfileMe.as_view(),      name='expert-profile-me'),
    path('<int:pk>/', ExpertProfileDetail.as_view(),  name='expert-profile-detail'),
]