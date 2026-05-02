# ======================================================
# File: users/views.py  (PATCHED)
# Changes:
#   1. LoginView: verifies Cloudflare Turnstile token before auth
#   2. RegisterView: verifies Cloudflare Turnstile token before registration
#   3. GoogleAuthView: added — handles Google One Tap credential
# ======================================================
import os
import requests as http_requests

from django.contrib.auth import get_user_model, logout
from rest_framework import viewsets, permissions, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token

from .serializers import CustomUserSerializer, UserLoginSerializer

CustomUser = get_user_model()

# ── Cloudflare Turnstile helper ────────────────────────────────────────────────
TURNSTILE_SECRET = os.environ.get("CF_TURNSTILE_SECRET_KEY", "")

def verify_turnstile(token: str, remote_ip: str = "") -> bool:
    """
    Returns True if the Turnstile token is valid.
    In development (secret key not set) always returns True.
    """
    if not TURNSTILE_SECRET or TURNSTILE_SECRET == "1x0000000000000000000000000000000AA":
        # Test/development secret — always passes
        return True
    if not token:
        return False
    try:
        resp = http_requests.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={
                "secret": TURNSTILE_SECRET,
                "response": token,
                "remoteip": remote_ip,
            },
            timeout=5,
        )
        return resp.json().get("success", False)
    except Exception:
        # Network error — fail open in dev, fail closed in prod
        return not bool(TURNSTILE_SECRET)


# ── Existing views (unchanged) ─────────────────────────────────────────────────
class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]


class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        return Response({
            "message": "Send a POST request with 'username', 'email', 'password' to register."
        }, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        # ── Turnstile check ────────────────────────────────────────────────────
        cf_token = request.data.get("cf_token", "")
        remote_ip = request.META.get("HTTP_CF_CONNECTING_IP") or request.META.get("REMOTE_ADDR", "")
        if not verify_turnstile(cf_token, remote_ip):
            return Response(
                {"error": "Security check failed. Please try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().create(request, *args, **kwargs)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        # ── Turnstile check ────────────────────────────────────────────────────
        cf_token = request.data.get("cf_token", "")
        remote_ip = request.META.get("HTTP_CF_CONNECTING_IP") or request.META.get("REMOTE_ADDR", "")
        if not verify_turnstile(cf_token, remote_ip):
            return Response(
                {"error": "Security check failed. Please try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = UserLoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'email': user.email,
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            request.user.auth_token.delete()
            logout(request)
            return Response({'detail': 'Successfully logged out.'}, status=status.HTTP_200_OK)
        except AttributeError:
            return Response({'detail': 'User is not logged in.'}, status=status.HTTP_400_BAD_REQUEST)


# ── NEW: Google OAuth ──────────────────────────────────────────────────────────
class GoogleAuthView(APIView):
    """
    Accepts a Google One Tap 'credential' (JWT), verifies it with Google,
    and returns a DRF token + user data — creating the user if first login.

    Prerequisites:
      pip install google-auth
      Set GOOGLE_CLIENT_ID in your environment variables.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        credential = request.data.get("credential")
        if not credential:
            return Response({"error": "Google credential is required."}, status=status.HTTP_400_BAD_REQUEST)

        google_client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
        if not google_client_id:
            return Response(
                {"error": "Google login is not configured on this server."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            from google.oauth2 import id_token
            from google.auth.transport import requests as google_requests

            id_info = id_token.verify_oauth2_token(
                credential,
                google_requests.Request(),
                google_client_id,
                clock_skew_in_seconds=10,
            )
        except ValueError as e:
            return Response({"error": f"Invalid Google token: {e}"}, status=status.HTTP_400_BAD_REQUEST)

        email = id_info.get("email")
        google_sub = id_info.get("sub")          # unique Google user ID
        given_name = id_info.get("given_name", "")
        family_name = id_info.get("family_name", "")

        if not email or not google_sub:
            return Response({"error": "Could not retrieve email from Google."}, status=status.HTTP_400_BAD_REQUEST)

        # Get or create user by email
        user, created = CustomUser.objects.get_or_create(
            email=email,
            defaults={
                # Derive a username from the email local part; make it unique
                "username": self._unique_username(email.split("@")[0]),
                "is_email_verified": True,   # Google emails are pre-verified
            }
        )

        # If user existed but wasn't Google-verified, mark them verified
        if not created and not getattr(user, "is_email_verified", True):
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified"])

        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "token": token.key,
            "user_id": user.pk,
            "username": user.username,
            "email": user.email,
        }, status=status.HTTP_200_OK)

    @staticmethod
    def _unique_username(base: str) -> str:
        """
        Ensures the derived username is unique by appending a counter if needed.
        """
        # Sanitise — only alphanumeric + underscores
        import re
        base = re.sub(r"[^\w]", "_", base)[:28]
        username = base
        counter = 1
        while CustomUser.objects.filter(username=username).exists():
            username = f"{base}_{counter}"
            counter += 1
        return username