from django.urls import path
from .views import ExpertProfileList, ExpertProfileDetail, ExpertProfileMe, ExpertProfileAvatarUpload, ExpertProfileEnsureView

urlpatterns = [
    path('',              ExpertProfileList.as_view(),        name='expert-profile-list'),
    path('me/',           ExpertProfileMe.as_view(),           name='expert-profile-me'),
    path('me/avatar/',    ExpertProfileAvatarUpload.as_view(), name='expert-profile-avatar'),
    path('ensure/',       ExpertProfileEnsureView.as_view(),    name='expert-profile-ensure'),
    path('<int:pk>/',     ExpertProfileDetail.as_view(),       name='expert-profile-detail'),
]