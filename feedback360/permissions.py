from rest_framework.permissions import BasePermission

from feedback360.views import user_has_admin_access


class IsAdminUser(BasePermission):
    def has_permission(self, request, view):
        return user_has_admin_access(request.user)

class HasSurveyCreationRights(BasePermission):
    def has_permission(self, request, view):
        return request.user.userrole_set.filter(
            Q(role__name='Администратор') |
            Q(role__name='Руководитель')
        ).exists()