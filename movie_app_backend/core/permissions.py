from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdminUser(BasePermission):
    """
    Allows access only to authenticated users who have the 'admin' role.
    """
    def has_permission(self, request, view):
        # Assumes user is authenticated first by IsAuthenticated
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.roles.filter(name='admin').exists()

class IsAdminOrReadOnly(BasePermission):
    """
    Allows read-only access for any authenticated user,
    but write access only to admin users.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Read permissions are allowed to any authenticated request
        if request.method in SAFE_METHODS: # ('GET', 'HEAD', 'OPTIONS')
            return True

        # Write permissions are only allowed to admin users
        return request.user.roles.filter(name='admin').exists()