from django.apps import AppConfig


class Feedback360Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'feedback360'

    def ready(self):
        # Импортируем сигналы здесь, если они есть
        pass