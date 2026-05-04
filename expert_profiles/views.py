from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ExpertProfile
from .serializers import ExpertProfileSerializer


class ExpertProfileList(generics.ListAPIView):
    # Highest-rated experts appear first.
    queryset = ExpertProfile.objects.all().order_by('-rating')
    serializer_class = ExpertProfileSerializer
    permission_classes = [permissions.IsAuthenticated]


class ExpertProfileDetail(generics.RetrieveUpdateAPIView):
    serializer_class = ExpertProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # Only experts have a profile — return a clear error if the user is a student
        try:
            return self.request.user.expert_profile
        except ExpertProfile.DoesNotExist:
            raise PermissionDenied("Only experts have a profile.")


class ExpertProfileMe(APIView):
    """
    GET  /api/expert-profiles/me/  → current expert's own profile
    PATCH /api/expert-profiles/me/ → update available / bio / field_of_study
    """
    permission_classes = [permissions.IsAuthenticated]

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
        # Only allow user-editable fields; everything else (ratings etc.) is read-only
        allowed = {k: v for k, v in request.data.items()
                   if k in ("available", "bio", "field_of_study")}
        serializer = ExpertProfileSerializer(profile, data=allowed, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)