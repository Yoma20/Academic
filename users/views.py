# ======================================================
# File: users/views.py
# Description: Defines API views for user actions.
# This version removes the session-based `login` function
# from the LoginView to resolve a potential RecursionError.
# ======================================================
from django.contrib.auth import get_user_model, logout
from rest_framework import viewsets, permissions, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from .serializers import CustomUserSerializer, UserLoginSerializer

CustomUser = get_user_model()

class CustomUserViewSet(viewsets.ModelViewSet):
    """
    A ViewSet for viewing and editing CustomUser instances.
    It's configured to allow unauthenticated users to create a new user.
    """
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    
    def get_permissions(self):
        """
        Custom permissions for the viewset.
        Allows 'create' (POST) for anyone, but all other actions require authentication.
        """
        if self.action == 'create':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

class RegisterView(generics.CreateAPIView):
    """
    A dedicated view for user registration. Publicly accessible.
    This view provides a helpful message for GET requests.
    """
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        """
        A custom GET method to provide a helpful message to users.
        """
        return Response({
            "message": "Send a POST request with 'username', 'email', 'password', and 'user_type' to register a new user."
        }, status=status.HTTP_200_OK)

class LoginView(APIView):
    """
    A view for user login. Publicly accessible.
    Authenticates the user and returns an auth token.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        # Pass request context to the serializer for authentication
        serializer = UserLoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        # The validated data contains the user object from the serializer
        user = serializer.validated_data['user']
        # Get or create the authentication token for the user
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'email': user.email
        }, status=status.HTTP_200_OK)

class LogoutView(APIView):
    """
    A view for user logout. Requires authentication.
    Deletes the user's auth token.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            # Delete the user's auth token and log out of the session
            request.user.auth_token.delete()
            logout(request)
            return Response({'detail': 'Successfully logged out.'}, status=status.HTTP_200_OK)
        except AttributeError:
            return Response({'detail': 'User is not logged in or has no token.'}, status=status.HTTP_400_BAD_REQUEST)
