from rest_framework import generics, permissions
from rest_framework.exceptions import NotFound, PermissionDenied
from .models import ExpertProfile
from .serializers import ExpertProfileSerializer


class ExpertProfileList(generics.ListAPIView):
    queryset = ExpertProfile.objects.all()
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
