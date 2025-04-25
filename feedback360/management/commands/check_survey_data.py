from django.core.management.base import BaseCommand
from feedback360.models import Survey, Question


class Command(BaseCommand):
    help = 'Проверяет целостность данных опросов'

    def handle(self, *args, **options):
        surveys = Survey.objects.all()

        for survey in surveys:
            questions = Question.objects.filter(
                competency__template=survey.template
            )

            self.stdout.write(f"Опрос: {survey.name} (ID: {survey.id})")
            self.stdout.write(f"Шаблон: {survey.template.name}")
            self.stdout.write(f"Количество вопросов: {questions.count()}")

            if questions.count() == 0:
                self.stdout.write(
                    self.style.ERROR("ОШИБКА: Нет вопросов в шаблоне!")
                )