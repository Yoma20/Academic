from rest_framework import serializers
from .models import Assignment, AssignmentBid
from users.serializers import CustomUserSerializer
from expert_profiles.serializers import ExpertProfileSerializer

class AssignmentSerializer(serializers.ModelSerializer):
    student = CustomUserSerializer(read_only=True)

    class Meta:
        model = Assignment
        fields = ['id', 'student', 'title', 'description', 'deadline', 'file', 'status', 'created_at', 'updated_at']
        read_only_fields = ['student', 'status']

class AssignmentBidSerializer(serializers.ModelSerializer):
    expert = ExpertProfileSerializer(read_only=True)
    assignment_title = serializers.CharField(source='assignment.title', read_only=True)

    class Meta:
        model = AssignmentBid
        fields = ['id', 'assignment', 'expert', 'price', 'message', 'created_at', 'assignment_title']
        read_only_fields = ['expert', 'assignment']

