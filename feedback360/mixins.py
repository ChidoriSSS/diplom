from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import AbstractUser
from django.shortcuts import redirect
from django.contrib import messages
from .models import UserRole


class LeaderRequiredMixin(UserPassesTestMixin):
    """Миксин для проверки прав руководителя"""

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_leader

    def handle_no_permission(self):
        messages.error(self.request, "Доступ только для руководителей")
        return redirect('dashboard')


class LeaderAccessMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and (
            self.request.user.userrole_set.filter(
                role__name='Руководитель'
            ).exists()
        )

    def handle_no_permission(self):
        messages.error(self.request, "Доступ только для руководителей")
        return redirect('dashboard')

class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and (
            self.request.user.is_superuser or
            self.request.user.userrole_set.filter(
                role__name__in=['Администратор']
            ).exists()
        )

    def handle_no_permission(self):
        messages.error(self.request, "У вас нет прав администратора")
        return redirect('dashboard')


def user_has_admin_access(user):
    return user.is_authenticated and (
        user.is_superuser
        or user.userrole_set.filter(
            role__name__in=['Администратор', 'Руководитель']
        ).exists()
    )
