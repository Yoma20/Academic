# assignments/permissions.py
from rest_framework import permissions

class IsStudent(permissions.BasePermission):
    """
    Custom permission to only allow users with 'student' user_type.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.user_type == 'student'

class IsExpert(permissions.BasePermission):
    """
    Custom permission to only allow users with 'expert' user_type.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.user_type == 'expert'

class IsAssignmentOwner(permissions.BasePermission):
    """
    Custom permission to only allow the owner of an assignment to modify or delete it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any authenticated request,
        # so we'll always allow GET, HEAD, or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions (PUT, PATCH, DELETE) are only allowed to the owner of the assignment.
        return obj.student == request.user

class IsBidExpert(permissions.BasePermission):
    """
    Custom permission to only allow the expert who made the bid to modify it.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.expert == request.user

