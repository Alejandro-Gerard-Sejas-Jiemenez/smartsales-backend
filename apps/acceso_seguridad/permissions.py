from rest_framework import permissions

class IsAdminRole(permissions.BasePermission):

    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return request.user.is_staff or request.user.rol == 'ADMIN'


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permiso personalizado:
    - CLIENTES pueden: Ver productos (GET, HEAD, OPTIONS)
    - ADMIN pueden: Hacer todo (GET, POST, PUT, PATCH, DELETE)
    """
    
    def has_permission(self, request, view):
        # Permitir métodos seguros (GET, HEAD, OPTIONS) para usuarios autenticados
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        # Para métodos de modificación (POST, PUT, PATCH, DELETE) solo ADMIN
        return request.user and request.user.is_authenticated and (
            request.user.is_staff or request.user.rol == 'ADMIN'
        )
