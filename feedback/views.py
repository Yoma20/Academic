from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Feedback
from .serializers import FeedbackSerializer


class FeedbackCreateView(APIView):
    """
    POST /api/feedback/
    Anonymous — no authentication required.
    Body: { report_type: 'bug'|'idea'|'category'|'other', message: str }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = FeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {'detail': 'Thank you for your feedback!'},
            status=status.HTTP_201_CREATED,
        )