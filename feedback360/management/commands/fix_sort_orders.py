from django.core.management.base import BaseCommand
from feedback360.models import Competency, Question


class Command(BaseCommand):
    help = 'Fix null sort orders'

    def handle(self, *args, **options):
        # Для компетенций
        Competency.objects.filter(sort_order__isnull=True).update(sort_order=0)

        # Для вопросов
        Question.objects.filter(sort_order__isnull=True).update(sort_order=0)

        self.stdout.write(self.style.SUCCESS("Sort orders fixed"))