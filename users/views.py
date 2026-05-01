from django.contrib.auth import get_user_model, logout
from django.conf import settings
from rest_framework import viewsets, permissions, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from .serializers import CustomUserSerializer, UserLoginSerializer
import resend

CustomUser = get_user_model()


def send_otp_email(to_email, username, otp, subject="Verify your TopMark account"):
    """Helper to send OTP emails via Resend."""
    resend.api_key = settings.RESEND_API_KEY
    try:
        resend.Emails.send({
            "from": settings.DEFAULT_FROM_EMAIL,
            "to": [to_email],
            "subject": subject,
            "html": f"""
                <div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;padding:32px;border:1px solid #e5e7eb;border-radius:12px;">
                    <h2 style="color:#1a1a2e;margin-bottom:8px;">TopMark Verification</h2>
                    <p style="color:#374151;">Hi <strong>{username}</strong>,</p>
                    <p style="color:#374151;">Your verification code is:</p>
                    <div style="font-size:2.5rem;font-weight:700;letter-spacing:12px;color:#1dbf73;text-align:center;padding:20px 0;">
                        {otp}
                    </div>
                    <p style="color:#6b7280;font-size:0.9rem;">This code expires in <strong>10 minutes</strong>.</p>
                    <p style="color:#6b7280;font-size:0.9rem;">If you did not create a TopMark account, you can safely ignore this email.</p>
                    <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;" />
                    <p style="color:#9ca3af;font-size:0.8rem;">— The TopMark Team &nbsp;|&nbsp; topmark.pro</p>
                </div>
            """,
        })
    except Exception as e:
        print(f"[Resend] Email send failed to {to_email}: {e}")


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
            "message": "POST username, email, password, user_type to register."
        }, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        otp = user.generate_and_save_otp()
        send_otp_email(user.email, user.username, otp)

        return Response({
            'message': 'Registration successful. Check your email for a 6-digit verification code.',
            'user_id': user.pk,
            'email': user.email,
        }, status=status.HTTP_201_CREATED)


class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        otp = request.data.get('otp', '').strip()

        if not user_id or not otp:
            return Response({'error': 'user_id and otp are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        if user.is_email_verified:
            return Response({'message': 'Email already verified.'}, status=status.HTTP_200_OK)

        if not user.is_otp_valid(otp):
            return Response(
                {'error': 'Invalid or expired code. Please request a new one.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.is_email_verified = True
        user.email_otp = None
        user.email_otp_created_at = None
        user.save(update_fields=['is_email_verified', 'email_otp', 'email_otp_created_at'])

        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'email': user.email,
        }, status=status.HTTP_200_OK)


class ResendOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        try:
            user = CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        if user.is_email_verified:
            return Response({'message': 'Email already verified.'}, status=status.HTTP_200_OK)

        otp = user.generate_and_save_otp()
        send_otp_email(
            user.email, user.username, otp,
            subject="Your new TopMark verification code"
        )
        return Response({'message': 'New code sent.'}, status=status.HTTP_200_OK)


class GoogleAuthView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        credential = request.data.get('credential')
        if not credential:
            return Response({'error': 'Google credential is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            idinfo = id_token.verify_oauth2_token(
                credential,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )
        except ValueError as e:
            return Response({'error': f'Invalid Google token: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        google_id = idinfo['sub']
        email = idinfo.get('email', '')
        given_name = idinfo.get('given_name', email.split('@')[0])

        user = CustomUser.objects.filter(google_id=google_id).first()
        if not user:
            user = CustomUser.objects.filter(email=email).first()
            if user:
                user.google_id = google_id
                user.is_email_verified = True
                user.save(update_fields=['google_id', 'is_email_verified'])
            else:
                username = email.split('@')[0]
                base = username
                counter = 1
                while CustomUser.objects.filter(username=username).exists():
                    username = f"{base}{counter}"
                    counter += 1

                user = CustomUser.objects.create_user(
                    username=username,
                    email=email,
                    password=None,
                    google_id=google_id,
                    is_email_verified=True,
                    user_type='student',
                )

        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'email': user.email,
        }, status=status.HTTP_200_OK)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = UserLoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        if not user.is_email_verified:
            otp = user.generate_and_save_otp()
            send_otp_email(
                user.email, user.username, otp,
                subject="Verify your TopMark account"
            )
            return Response({
                'error': 'email_not_verified',
                'message': 'Please verify your email. A new code has been sent.',
                'user_id': user.pk,
                'email': user.email,
            }, status=status.HTTP_403_FORBIDDEN)

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
            return Response({'detail': 'Not logged in.'}, status=status.HTTP_400_BAD_REQUEST)