# users/views.py
import os
import re
import requests as http_requests

from django.contrib.auth import get_user_model, login as auth_login, logout as auth_logout
from django.conf import settings
from rest_framework import viewsets, permissions, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    CustomUserSerializer,
    UserLoginSerializer,
    ProfileUpdateSerializer,
    ChangePasswordSerializer,
)

CustomUser = get_user_model()

# ── Cloudflare Turnstile ───────────────────────────────────────────────────────
TURNSTILE_SECRET = os.environ.get("CF_TURNSTILE_SECRET_KEY", "")

from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse

@ensure_csrf_cookie
def csrf_token_view(request):
    return JsonResponse({"detail": "CSRF cookie set"}) 

def verify_turnstile(token: str, remote_ip: str = "") -> bool:
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
    """Consistent user shape returned to the frontend on every auth action.
    No token — the session cookie handles auth from here on.
    """
    return {
        "user_id":   user.pk,
        "username":  user.username,
        "email":     user.email,
        "user_type": user.user_type,
        "isSeller":  user.user_type == "expert",
    }


def _send_otp_email(user):
    """Generate a fresh OTP, save it, and email it via Resend HTTP API."""
    otp = user.generate_and_save_otp()
    api_key = os.environ.get("RESEND_API_KEY", "")
    if not api_key:
        print("[OTP email error] RESEND_API_KEY is not set.")
        return
    try:
        resp = http_requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": settings.DEFAULT_FROM_EMAIL,
                "to": [user.email],
                "subject": "Your TopMark verification code",
                "text": (
                    f"Hi {user.username},\n\n"
                    f"Your 6-digit verification code is: {otp}\n\n"
                    f"It expires in 10 minutes.\n\n"
                    f"— The TopMark Team"
                ),
            },
            timeout=10,
        )
        if resp.status_code not in (200, 201):
            print(f"[OTP email error] Resend API returned {resp.status_code}: {resp.text}")
    except Exception as e:
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
        cf_token  = request.data.get("cf_token", "")
        remote_ip = request.META.get("HTTP_CF_CONNECTING_IP") or request.META.get("REMOTE_ADDR", "")
        if not verify_turnstile(cf_token, remote_ip):
            return Response({"error": "Security check failed. Please try again."},
                            status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
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
    On success, logs the user in (creates a session) and returns the user payload.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        user_id = request.data.get("user_id")
        otp     = request.data.get("otp", "")

        try:
            user = CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if user.is_email_verified:
            # Already verified — just log in and return
            auth_login(request, user)
            return Response(_user_payload(user), status=status.HTTP_200_OK)

        if not user.is_otp_valid(otp):
            return Response(
                {"error": "Invalid or expired code. Request a new one."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_email_verified = True
        user.email_otp = None
        user.save(update_fields=["is_email_verified", "email_otp"])

        auth_login(request, user)
        return Response(_user_payload(user), status=status.HTTP_200_OK)


# ── Resend OTP ─────────────────────────────────────────────────────────────────
class ResendOtpView(APIView):
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
        cf_token  = request.data.get("cf_token", "")
        remote_ip = request.META.get("HTTP_CF_CONNECTING_IP") or request.META.get("REMOTE_ADDR", "")
        if not verify_turnstile(cf_token, remote_ip):
            return Response({"error": "Security check failed. Please try again."},
                            status=status.HTTP_400_BAD_REQUEST)

        serializer = UserLoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        if not user.is_email_verified:
            _send_otp_email(user)
            return Response(
                {"error": "email_not_verified", "user_id": user.pk, "email": user.email},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Create Django session — browser receives a sessionid cookie
        auth_login(request, user)
        return Response(_user_payload(user), status=status.HTTP_200_OK)


# ── Logout ─────────────────────────────────────────────────────────────────────
class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        auth_logout(request)
        return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)


# ── Google OAuth ───────────────────────────────────────────────────────────────
class GoogleAuthView(APIView):
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

        auth_login(request, user)
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


# ── Me — GET / PATCH profile ──────────────────────────────────────────────────
class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        pic  = user.profile_picture
        picture_url = request.build_absolute_uri(pic.url) if pic else None
        return Response({
            "id":              user.pk,
            "username":        user.username,
            "email":           user.email,
            "first_name":      user.first_name,
            "last_name":       user.last_name,
            "user_type":       user.user_type,
            "profile_picture": picture_url,
        }, status=status.HTTP_200_OK)

    def patch(self, request, *args, **kwargs):
        serializer = ProfileUpdateSerializer(
            request.user, data=request.data, partial=True,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        pic  = user.profile_picture
        picture_url = request.build_absolute_uri(pic.url) if pic else None
        return Response(
            {"detail": "Profile updated.", **serializer.data,
             "profile_picture": picture_url},
            status=status.HTTP_200_OK,
        )


# ── Change password ────────────────────────────────────────────────────────────
class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Re-login so the session stays valid after password change
        auth_login(request, user)

        return Response(
            {"detail": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )