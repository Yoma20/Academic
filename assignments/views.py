from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from .models import Assignment, AssignmentBid
from .serializers import AssignmentSerializer, AssignmentBidSerializer

class IsStudent(permissions.BasePermission):
    """Custom permission to only allow students to create assignments."""
    def has_permission(self, request, view):
        # Allow read-only access for anyone, but write access only for students
        if request.method in permissions.SAFE_METHODS:
            return True
        # Check if the user is authenticated and then check for is_student attribute
        return request.user and request.user.is_authenticated and hasattr(request.user, 'is_student') and request.user.is_student

class AssignmentListCreateView(generics.ListCreateAPIView):
    queryset = Assignment.objects.all().order_by('-created_at')
    serializer_class = AssignmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsStudent]

    def perform_create(self, serializer):
        # Associate the assignment with the logged-in student user
        serializer.save(student=self.request.user)

class AssignmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        obj = super().get_object()
        # Allow students to view/update/delete their own assignments.
        # Allow experts to view assignments.
        if self.request.user.is_student and obj.student != self.request.user:
            raise PermissionDenied("You do not have permission to access this assignment.")
        return obj

class BidListForAssignmentView(generics.ListAPIView):
    serializer_class = AssignmentBidSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        assignment_id = self.kwargs['assignment_id']
        return AssignmentBid.objects.filter(assignment__id=assignment_id).order_by('-created_at')

class AssignmentBidListCreateView(generics.ListCreateAPIView):
    queryset = AssignmentBid.objects.all().order_by('-created_at')
    serializer_class = AssignmentBidSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Associate the bid with the logged-in expert user
        if not hasattr(self.request.user, 'expert_profile'):
            raise PermissionDenied("Only experts can place bids.")
        serializer.save(expert=self.request.user.expert_profile)

class AssignmentBidDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = AssignmentBid.objects.all()
    serializer_class = AssignmentBidSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        obj = super().get_object()
        # Allow experts to view/update/delete their own bids.
        # Allow students to view bids on their assignments.
        if self.request.user.is_expert and obj.expert.user == self.request.user:
            return obj
        elif self.request.user.is_student and obj.assignment.student == self.request.user:
            return obj
        else:
            raise PermissionDenied("You do not have permission to access this bid.")
