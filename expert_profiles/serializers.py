from rest_framework import serializers
from .models import ExpertProfile

class ExpertProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = ExpertProfile
        fields = ['id', 'username', 'email', 'field_of_study', 'bio', 'available', 'rating']

