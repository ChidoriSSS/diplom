from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db.models import Q

from feedback360.models import (
    Role, SurveyTemplate, Question,
    Survey, Respondent, Rater, Report, Response,
    UserRole
)
from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class Command(BaseCommand):
    help = 'Загружает тестовые данные: пользователей, роли, шаблоны опросов и демо-опрос'

    def clear_existing_data(self):
        """Очистка существующих тестовых данных"""
        Response.objects.all().delete()
        Rater.objects.all().delete()
        Respondent.objects.all().delete()
        Report.objects.all().delete()
        Survey.objects.all().delete()
        Question.objects.all().delete()
        SurveyTemplate.objects.all().delete()
        UserRole.objects.all().delete()

        test_usernames = [user['username'] for user in self.get_test_users()]
        User.objects.filter(username__in=test_usernames).delete()

    def get_test_users(self):
        return [
            {
                'username': 'admin1',
                'email': 'admin1@company.com',
                'first_name': 'Александр',
                'last_name': 'Иванов',
                'position': 'Генеральный директор',
                'department': 'Руководство',
                'is_staff': True,
                'is_superuser': True,
                'password': 'admin123',
                'roles': ['Администратор']
            },
            {
                'username': 'admin',
                'email': 'admin@company.com',
                'first_name': 'Иван',
                'last_name': 'Петров',
                'position': 'Директор',
                'department': 'Руководство',
                'is_staff': True,
                'is_superuser': True,
                'password': 'admin123',
                'roles': ['Администратор']
            },
            {
                'username': 'leader1',
                'email': 'leader1@company.com',
                'first_name': 'Елена',
                'last_name': 'Петрова',
                'position': 'Директор по персоналу',
                'department': 'Управление персоналом',
                'password': 'leader123',
                'roles': ['Руководитель', 'Администратор']
            },
            {
                'username': 'manager1',
                'email': 'manager1@company.com',
                'first_name': 'Сергей',
                'last_name': 'Кузнецов',
                'position': 'Директор по продажам',
                'department': 'Продажи',
                'password': 'manager123',
                'roles': ['Руководитель']
            },
            {
                'username': 'employee1',
                'email': 'employee1@company.com',
                'first_name': 'Иван',
                'last_name': 'Федоров',
                'position': 'Менеджер по продажам',
                'department': 'Продажи',
                'password': 'employee123',
                'roles': ['Сотрудник']
            }
        ]

    def init_users_and_roles(self):
        roles = {
            'Администратор': Role.objects.get_or_create(name='Администратор')[0],
            'Руководитель': Role.objects.get_or_create(name='Руководитель')[0],
            'Сотрудник': Role.objects.get_or_create(name='Сотрудник')[0]
        }

        for user_data in self.get_test_users():
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'email': user_data['email'],
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                    'position': user_data['position'],
                    'department': user_data['department'],
                    'is_staff': user_data.get('is_staff', False),
                    'is_superuser': user_data.get('is_superuser', False)
                }
            )

            if created:
                user.set_password(user_data['password'])
                user.save()

            for role_name in user_data.get('roles', []):
                if role_name in roles:
                    UserRole.objects.get_or_create(user=user, role=roles[role_name])

    def create_survey_template(self, config):
        try:
            template, created = SurveyTemplate.objects.get_or_create(name=config['name'])

            if created:
                for q_data in config['questions']:
                    if q_data['type'] == 'scale':
                        Question.objects.create(
                            text=q_data['text'],
                            template=template,
                            answer_type='scale',
                            scale_min=1,
                            scale_max=5,
                            scale_choices=[
                                [1, "1 - Никогда"],
                                [2, "2 - Редко"],
                                [3, "3 - Иногда"],
                                [4, "4 - Часто"],
                                [5, "5 - Всегда"]
                            ]
                        )
                    else:
                        Question.objects.create(
                            text=q_data['text'],
                            template=template,
                            answer_type='text'
                        )
            return template
        except Exception as e:
            logger.error(f"Ошибка: {str(e)}")
            raise

    def init_templates(self):
        templates_config = [
            {
                'name': 'Оценка руководителя 360°',
                'questions': [
                    {'text': 'Приведите примеры эффективного разрешения конфликтов в команде', 'type': 'text'},
                    {'text': 'Оцените способность принимать сложные решения', 'type': 'scale'},
                    {'text': 'Насколько руководитель открыт для обратной связи?', 'type': 'scale'}
                ]
            },
            {
                'name': 'Оценка сотрудника',
                'questions': [
                    {'text': 'Оцените способность работать без контроля', 'type': 'scale'},
                    {'text': 'Как сотрудник реагирует на стрессовые ситуации?', 'type': 'text'}
                ]
            }
        ]

        for config in templates_config:
            self.create_survey_template(config)

    def create_demo_survey(self):
        try:
            template = SurveyTemplate.objects.get(name='Оценка руководителя 360°')
            admin_user = User.objects.get(username='admin1')

            survey = Survey.objects.create(
                name='Демо-опрос 2024',
                template=template,
                start_date=date.today(),
                end_date=date.today() + timedelta(days=14),
                status='active',
                created_by=admin_user
            )

            respondent = Respondent.objects.create(
                survey=survey,
                user=User.objects.get(username='manager1'),
                manager=admin_user
            )

            Rater.objects.create(
                respondent=respondent,
                user=User.objects.get(username='employee1'),
                relationship_type='peer'
            )

        except Exception as e:
            logger.error(f"Ошибка создания демо-опроса: {str(e)}")

    def handle(self, *args, **options):
        self.stdout.write("1. Очистка старых данных...")
        self.clear_existing_data()

        self.stdout.write("2. Создание пользователей...")
        self.init_users_and_roles()

        self.stdout.write("3. Создание шаблонов...")
        self.init_templates()

        self.stdout.write("4. Создание демо-опроса...")
        self.create_demo_survey()

        self.stdout.write(self.style.SUCCESS(
            "Тестовые данные успешно загружены!\n"
            "Администратор: admin1/admin123\n"
            "Менеджер: manager1/manager123\n"
            "Сотрудник: employee1/employee123"
        ))