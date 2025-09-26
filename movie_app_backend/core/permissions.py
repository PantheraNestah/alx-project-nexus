from rest_framework.permissions import BasePermission

class IsAdminUser(BasePermission):
    """
    Allows access only to users with the 'admin' role.
    """
    def has_permission(self, request, view):
        # Assumes user is authenticated first by IsAuthenticated
        if not request.user.is_authenticated:
            return False
        return request.user.roles.filter(name='admin').exists()

class IsAdminOrReadOnly(BasePermission):
    """
    Allows read-only access for any authenticated user,
    but write access only to admin users.
    """
    def has_permission(self, request, view):
        # Read permissions are allowed to any authenticated request
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return request.user and request.user.is_authenticated

        # Write permissions are only allowed to admin users
        return request.user and request.user.is_authenticated and request.user.roles.filter(name='admin').exists()