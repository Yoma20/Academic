from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import (
    CustomUserViewSet,
    RegisterView,
    LoginView,
    LogoutView,
    GoogleAuthView,
    VerifyEmailView,
    ResendOtpView,
    MeView,
    ChangePasswordView,
)

router = SimpleRouter()
router.register(r'manage', CustomUserViewSet, basename='user')

urlpatterns = [
    path('register/',         RegisterView.as_view(),       name='register'),
    path('login/',            LoginView.as_view(),           name='login'),
    path('logout/',           LogoutView.as_view(),          name='logout'),
    path('google-auth/',      GoogleAuthView.as_view(),      name='google-auth'),
    path('verify-email/',     VerifyEmailView.as_view(),     name='verify-email'),
    path('resend-otp/',       ResendOtpView.as_view(),       name='resend-otp'),
    path('me/',               MeView.as_view(),              name='me'),
    path('change-password/',  ChangePasswordView.as_view(),  name='change-password'),
    path('',                  include(router.urls)),
]