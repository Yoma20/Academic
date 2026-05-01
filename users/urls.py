from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import (
    CustomUserViewSet, RegisterView, LoginView, LogoutView,
    VerifyEmailView, ResendOTPView, GoogleAuthView,
)

router = SimpleRouter()
router.register(r'manage', CustomUserViewSet, basename='user')

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend-otp'),
    path('google-auth/', GoogleAuthView.as_view(), name='google-auth'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('', include(router.urls)),
]