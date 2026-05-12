from django.urls import path, include
from rest_framework.routers import SimpleRouter
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET
from django.http import JsonResponse
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

@require_GET
@ensure_csrf_cookie
def get_csrf(request):
    return JsonResponse({"detail": "CSRF cookie set"})

urlpatterns = [
    path('csrf/',             get_csrf,                      name='csrf'),        
    path('register/',         RegisterView.as_view(),        name='register'),
    path('login/',            LoginView.as_view(),            name='login'),
    path('logout/',           LogoutView.as_view(),           name='logout'),
    path('google-auth/',      GoogleAuthView.as_view(),       name='google-auth'),
    path('verify-email/',     VerifyEmailView.as_view(),      name='verify-email'),
    path('resend-otp/',       ResendOtpView.as_view(),        name='resend-otp'),
    path('me/',               MeView.as_view(),               name='me'),
    path('change-password/',  ChangePasswordView.as_view(),   name='change-password'),
    path('',                  include(router.urls)),
]