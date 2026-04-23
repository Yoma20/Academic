from rest_framework import serializers
from .models import Dispute, DisputeEvidence


class DisputeEvidenceSerializer(serializers.ModelSerializer):
    submitted_by_username = serializers.CharField(
        source='submitted_by.username', read_only=True
    )

    class Meta:
        model = DisputeEvidence
        fields = [
            'id', 'dispute', 'submitted_by', 'submitted_by_username',
            'submitted_by_role', 'description', 'file', 'created_at',
        ]
        read_only_fields = ['submitted_by', 'submitted_by_role', 'dispute']


class DisputeSerializer(serializers.ModelSerializer):
    evidence = DisputeEvidenceSerializer(many=True, read_only=True)
    opened_by_username = serializers.CharField(
        source='opened_by.username', read_only=True
    )
    order_gig_title = serializers.CharField(
        source='order.package.gig.title', read_only=True
    )
    payment_status = serializers.CharField(
        source='order.payment_status', read_only=True
    )

    class Meta:
        model = Dispute
        fields = [
            'id', 'order', 'order_gig_title', 'payment_status',
            'opened_by', 'opened_by_username', 'reason', 'status',
            'resolution_notes', 'resolved_by', 'evidence',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'opened_by', 'status', 'resolution_notes', 'resolved_by',
        ]