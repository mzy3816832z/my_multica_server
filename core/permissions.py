"""
权限类
"""
from rest_framework import permissions
from .exceptions import ForbiddenException


class IsTenant(permissions.BasePermission):
    """
    仅租客可访问
    """
    message = '仅租客可访问'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'role', None) == 'tenant'
        )


class IsLandlord(permissions.BasePermission):
    """
    仅商家可访问
    """
    message = '仅商家可访问'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'role', None) == 'landlord'
        )


class IsAdmin(permissions.BasePermission):
    """
    仅管理员可访问
    """
    message = '仅管理员可访问'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'role', None) == 'admin'
        )
