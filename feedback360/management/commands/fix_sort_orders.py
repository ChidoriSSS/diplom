from django.core.management.base import BaseCommand
from feedback360.models import Competency, Question


class Command(BaseCommand):
    help = 'Fix null sort orders'

    def handle(self, *args, **options):
        # Для вопросов в шаблонах
        for template in SurveyTemplate.objects.all():
            for idx, question in enumerate(template.template_questions.order_by('sort_order'), 1):
                question.sort_order = idx
                question.save()