# permissions.py
from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """
    Allows access only to admin users.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class IsOperator(permissions.BasePermission):
    """
    Allows access to operators and admins.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['admin', 'operator']


class IsViewer(permissions.BasePermission):
    """
    Base permission for all authenticated users (admin, operator, viewer).
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Allows read-only access to all authenticated users,
    but only admin users can perform write operations.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_authenticated and request.user.role == 'admin'


class IsOperatorOrReadOnly(permissions.BasePermission):
    """
    Allows read-only access to all authenticated users,
    but only admin and operator users can perform write operations.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_authenticated and request.user.role in ['admin', 'operator']


class IsOwnerOrStaffReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object to edit it.
    Staff can view but not edit.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated

        # Write permissions are only allowed to the owner
        # Assumes the model has a 'created_by' or 'user' attribute
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        elif hasattr(obj, 'user'):
            return obj.user == request.user
        return False