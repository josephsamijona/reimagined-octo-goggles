from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    """Only allows access to users with role ADMIN."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'ADMIN')


class IsClientUser(BasePermission):
    """Only allows access to users with role CLIENT."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'CLIENT')


class IsInterpreterUser(BasePermission):
    """Only allows access to users with role INTERPRETER."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'INTERPRETER')


class IsAdminOrReadOnly(BasePermission):
    """Admin can write, others can only read."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return request.user.role == 'ADMIN'
