from django.core.management.base import BaseCommand
from feedback360.models import Report


class Command(BaseCommand):
    help = 'Генерирует отчеты для всех существующих записей'

    def handle(self, *args, **options):
        reports = Report.objects.all()
        for report in reports:
            report.generate_report_data()
            self.stdout.write(f"Обновлен отчет #{report.id}")

        self.stdout.write(self.style.SUCCESS(f"Обработано {reports.count()} отчетов"))