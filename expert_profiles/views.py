from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from users.models import SiteSettings
from .models import ExpertProfile
from .serializers import ExpertProfileSerializer

# Fields the expert is allowed to update themselves
EDITABLE_FIELDS = {
    "available", "bio", "field_of_study", "title",
    "skills", "languages", "country",
    "work_experience", "education", "certifications",
}


class ExpertProfileEnsureView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if request.user.user_type != 'expert':
            return Response(
                {"detail": "Only expert accounts can have an expert profile."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # ── Expert registration gate ──────────────────────────────────────────
        if not SiteSettings.get().expert_registration_open:
            return Response(
                {"detail": "Expert applications are currently closed."},
                status=status.HTTP_403_FORBIDDEN,
            )

        profile, created = ExpertProfile.objects.get_or_create(user=request.user)
        serializer = ExpertProfileSerializer(profile)
        return Response(
            {**serializer.data, "created": created},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        ) 
    
class ExpertProfileList(generics.ListAPIView):
    """GET /api/expert-profiles/ — list all experts, highest-rated first."""
    queryset           = ExpertProfile.objects.all().order_by('-rating')
    serializer_class   = ExpertProfileSerializer
    permission_classes = [permissions.IsAuthenticated]


class ExpertProfileDetail(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/expert-profiles/<pk>/"""
    serializer_class   = ExpertProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        try:
            return self.request.user.expert_profile
        except ExpertProfile.DoesNotExist:
            raise PermissionDenied("Only experts have a profile.")


class ExpertProfileMe(APIView):
    """
    GET   /api/expert-profiles/me/        → current expert's own profile
    PATCH /api/expert-profiles/me/        → update editable fields (JSON)
    POST  /api/expert-profiles/me/avatar/ → upload profile picture
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes     = [MultiPartParser, FormParser, JSONParser]

    def _get_profile(self, user):
        try:
            return user.expert_profile
        except ExpertProfile.DoesNotExist:
            raise PermissionDenied("Only experts have a profile.")

    def get(self, request, *args, **kwargs):
        profile = self._get_profile(request.user)
        return Response(ExpertProfileSerializer(profile).data)

    def patch(self, request, *args, **kwargs):
        profile = self._get_profile(request.user)

        # Strip out any fields the expert is not allowed to change
        allowed = {k: v for k, v in request.data.items() if k in EDITABLE_FIELDS}

        serializer = ExpertProfileSerializer(profile, data=allowed, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class ExpertProfileAvatarUpload(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes     = [MultiPartParser, FormParser, JSONParser]

    def _get_profile(self, user):
        try:
            return user.expert_profile
        except ExpertProfile.DoesNotExist:
            raise PermissionDenied("Only experts have a profile.")

    def post(self, request, *args, **kwargs):
        profile = self._get_profile(request.user)
        url = request.data.get("avatar_url")

        if not url:
            return Response(
                {"error": "No URL provided. Send the image URL with key 'avatar_url'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile.avatar_url = url
        profile.save(update_fields=["avatar_url"])

        # Sync to CustomUser.profile_picture so everything reads from one place
        request.user.profile_picture = url
        request.user.save(update_fields=["profile_picture"])

        return Response({"avatar_url": url}, status=status.HTTP_200_OK)

class ExpertProfileEnsureView(APIView):
    """
    POST /api/expert-profiles/ensure/
    Creates an ExpertProfile for the current user if one does not already exist.
    Safe to call multiple times (idempotent). Fixes existing expert accounts
    that were registered before the auto-create signal was in place.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if request.user.user_type != 'expert':
            return Response(
                {"detail": "Only expert accounts can have an expert profile."},
                status=status.HTTP_403_FORBIDDEN,
            )
        profile, created = ExpertProfile.objects.get_or_create(user=request.user)
        serializer = ExpertProfileSerializer(profile)
        return Response(
            {**serializer.data, "created": created},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )