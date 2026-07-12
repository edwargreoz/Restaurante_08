

from rest_framework.permissions import BasePermission

class EsMozo (BasePermission):
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        return request.user.groups.filter(name='Mozo').exists()

class EsCocinero(BasePermission):
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        return request.user.groups.filter(name='Cocinero').exists()
    
class EsCajero(BasePermission):
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        return request.user.groups.filter(name='Cajero').exists()
class EsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_superuser