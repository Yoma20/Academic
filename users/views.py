# users/views.py
import os
import re
import requests as http_requests

from django.contrib.auth import get_user_model, logout
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import viewsets, permissions, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token

from .serializers import CustomUserSerializer, UserLoginSerializer

CustomUser = get_user_model()

# ── Cloudflare Turnstile ───────────────────────────────────────────────────────
TURNSTILE_SECRET = os.environ.get("CF_TURNSTILE_SECRET_KEY", "")

def verify_turnstile(token: str, remote_ip: str = "") -> bool:
    # Any test/dev key (starts with 1x0000) always passes
    if not TURNSTILE_SECRET or TURNSTILE_SECRET.startswith("1x0000"):
        return True
    if not token:
        return False
    try:
        resp = http_requests.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={"secret": TURNSTILE_SECRET, "response": token, "remoteip": remote_ip},
            timeout=5,
        )
        return resp.json().get("success", False)
    except Exception:
        return not bool(TURNSTILE_SECRET)


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _user_payload(user):
    """Single consistent response shape used by every auth endpoint."""
    token, _ = Token.objects.get_or_create(user=user)
    return {
        "token":     token.key,
        "user_id":   user.pk,
        "username":  user.username,
        "email":     user.email,
        "user_type": user.user_type,             # 'student' | 'expert'
        "isSeller":  user.user_type == "expert", # convenience bool for frontend
    }

def _send_otp_email(user):
    """Generate a fresh OTP, save it, and email it to the user."""
    otp = user.generate_and_save_otp()
    try:
        send_mail(
            subject="Your TopMark verification code",
            message=(
                f"Hi {user.username},\n\n"
                f"Your 6-digit verification code is: {otp}\n\n"
                f"It expires in 10 minutes.\n\n"
                f"— The TopMark Team"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception as e:
        # Log but don't crash — OTP is still stored in the DB
        print(f"[OTP email error] {e}")


# ── ViewSet (admin CRUD) ───────────────────────────────────────────────────────
class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer

    def get_permissions(self):
        if self.action == "create":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]


# ── Register ───────────────────────────────────────────────────────────────────
class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        return Response(
            {"message": "POST with username, email, password to register."},
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        # Turnstile
        cf_token  = request.data.get("cf_token", "")
        remote_ip = request.META.get("HTTP_CF_CONNECTING_IP") or request.META.get("REMOTE_ADDR", "")
        if not verify_turnstile(cf_token, remote_ip):
            return Response({"error": "Security check failed. Please try again."},
                            status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Send OTP so the user can verify their email
        _send_otp_email(user)

        return Response(
            {"user_id": user.pk, "email": user.email,
             "message": "Account created. Check your email for your verification code."},
            status=status.HTTP_201_CREATED,
        )


# ── Verify Email ───────────────────────────────────────────────────────────────
class VerifyEmailView(APIView):
    """
    POST /api/users/verify-email/
    Body: { user_id, otp }
    Returns the full auth payload on success so the frontend can log the user in immediately.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        user_id = request.data.get("user_id")
        otp     = request.data.get("otp", "")

        try:
            user = CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        # Already verified — just hand back a token
        if user.is_email_verified:
            return Response(_user_payload(user), status=status.HTTP_200_OK)

        if not user.is_otp_valid(otp):
            return Response(
                {"error": "Invalid or expired code. Request a new one."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_email_verified = True
        user.email_otp = None
        user.save(update_fields=["is_email_verified", "email_otp"])

        return Response(_user_payload(user), status=status.HTTP_200_OK)


# ── Resend OTP ─────────────────────────────────────────────────────────────────
class ResendOtpView(APIView):
    """
    POST /api/users/resend-otp/
    Body: { user_id }
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        user_id = request.data.get("user_id")
        try:
            user = CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if user.is_email_verified:
            return Response({"message": "Email is already verified."}, status=status.HTTP_200_OK)

        _send_otp_email(user)
        return Response({"message": "New code sent."}, status=status.HTTP_200_OK)


# ── Login ──────────────────────────────────────────────────────────────────────
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        # Turnstile
        cf_token  = request.data.get("cf_token", "")
        remote_ip = request.META.get("HTTP_CF_CONNECTING_IP") or request.META.get("REMOTE_ADDR", "")
        if not verify_turnstile(cf_token, remote_ip):
            return Response({"error": "Security check failed. Please try again."},
                            status=status.HTTP_400_BAD_REQUEST)

        serializer = UserLoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        # Block unverified accounts — resend OTP automatically
        if not user.is_email_verified:
            _send_otp_email(user)
            return Response(
                {"error": "email_not_verified", "user_id": user.pk, "email": user.email},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(_user_payload(user), status=status.HTTP_200_OK)


# ── Logout ─────────────────────────────────────────────────────────────────────
class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            request.user.auth_token.delete()
            logout(request)
            return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)
        except AttributeError:
            return Response({"detail": "User is not logged in."}, status=status.HTTP_400_BAD_REQUEST)


# ── Google OAuth ───────────────────────────────────────────────────────────────
class GoogleAuthView(APIView):
    """
    POST /api/users/google-auth/
    Body: { credential }  — Google One Tap JWT
    Creates the user on first login; returns the same payload as LoginView.
    Prerequisites: pip install google-auth  |  GOOGLE_CLIENT_ID env var set.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        credential = request.data.get("credential")
        if not credential:
            return Response({"error": "Google credential is required."},
                            status=status.HTTP_400_BAD_REQUEST)

        google_client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
        if not google_client_id:
            return Response({"error": "Google login is not configured on this server."},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)

        try:
            from google.oauth2 import id_token
            from google.auth.transport import requests as google_requests
            id_info = id_token.verify_oauth2_token(
                credential, google_requests.Request(), google_client_id,
                clock_skew_in_seconds=10,
            )
        except ValueError as e:
            return Response({"error": f"Invalid Google token: {e}"},
                            status=status.HTTP_400_BAD_REQUEST)

        email      = id_info.get("email")
        google_sub = id_info.get("sub")

        if not email or not google_sub:
            return Response({"error": "Could not retrieve email from Google."},
                            status=status.HTTP_400_BAD_REQUEST)

        user, created = CustomUser.objects.get_or_create(
            email=email,
            defaults={
                "username":          self._unique_username(email.split("@")[0]),
                "is_email_verified": True,
            },
        )

        if not created and not getattr(user, "is_email_verified", True):
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified"])

        return Response(_user_payload(user), status=status.HTTP_200_OK)

    @staticmethod
    def _unique_username(base: str) -> str:
        base     = re.sub(r"[^\w]", "_", base)[:28]
        username = base
        counter  = 1
        while CustomUser.objects.filter(username=username).exists():
            username = f"{base}_{counter}"
            counter += 1
        return username