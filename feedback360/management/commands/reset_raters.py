from django.core.management.base import BaseCommand
from feedback360.models import Rater, Response

class Command(BaseCommand):
    help = 'Сбрасывает статусы оценивающих'

    def handle(self, *args, **options):
        Rater.objects.filter(status='started').update(status='pending')
        Response.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("Все оценки сброшены!"))