class RoleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Добавляем проверку наличия атрибута user
        if hasattr(request, 'user'):
            user = request.user
            # Проверяем аутентификацию
            if user.is_authenticated:
                user.is_employee = not (
                    user.is_superuser or
                    user.userrole_set.filter(
                        role__name__in=['Администратор', 'Руководитель']
                    ).exists()
                )
        return self.get_response(request)