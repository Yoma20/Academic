from rest_framework import serializers
from .models import ExpertProfile


class ExpertProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email    = serializers.EmailField(source='user.email',    read_only=True)

    class Meta:
        model  = ExpertProfile
        fields = [
            'id', 'username', 'email',
            # Editable by the expert
            'field_of_study', 'bio', 'title', 'available',
            'skills', 'languages', 'country', 'avatar_url',
            'work_experience', 'education', 'certifications',
            # Read-only aggregates
            'rating', 'avg_rubric_adherence', 'avg_timeliness',
            'avg_communication', 'total_reviews', 'recommendation_rate',
            
        ]
        read_only_fields = [
            'rating', 'avg_rubric_adherence', 'avg_timeliness',
            'avg_communication', 'total_reviews', 'recommendation_rate',
            
        ]

        def validate_user_type(self, value):
            if value == 'admin':
                raise serializers.ValidationError("Invalid user type.")
            return value

                