from rest_framework import generics, permissions
from .models import ExpertProfile
from .serializers import ExpertProfileSerializer

class ExpertProfileList(generics.ListAPIView):
    queryset = ExpertProfile.objects.all()
    serializer_class = ExpertProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

class ExpertProfileDetail(generics.RetrieveUpdateAPIView):
    queryset = ExpertProfile.objects.all()
    serializer_class = ExpertProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # Allow experts to retrieve and update their own profile
        return self.request.user.expert_profile
