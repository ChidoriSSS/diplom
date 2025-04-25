from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db.models import Q

from feedback360.models import (
    Role, SurveyTemplate, Competency, Question,
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
        # Удаление в правильном порядке зависимостей
        Response.objects.all().delete()
        Rater.objects.all().delete()
        Respondent.objects.all().delete()
        Report.objects.all().delete()
        Survey.objects.all().delete()
        Question.objects.all().delete()
        Competency.objects.all().delete()
        SurveyTemplate.objects.all().delete()
        UserRole.objects.all().delete()

        # Удаление только тестовых пользователей
        test_usernames = [user['username'] for user in self.get_test_users()]
        User.objects.filter(username__in=test_usernames).delete()

    def get_test_users(self):
        """Список тестовых пользователей"""
        return [
            # Основной администратор
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
            # Дополнительный администратор
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

            # HR-отдел
            {
                'username': 'hr1', 'email': 'hr1@company.com',
                'first_name': 'Елена', 'last_name': 'Петрова',
                'position': 'HR-директор', 'department': 'HR',
                'password': 'hr123', 'roles': ['HR', 'Администратор']
            },
            {
                'username': 'hr2', 'email': 'hr2@company.com',
                'first_name': 'Ольга', 'last_name': 'Сидорова',
                'position': 'HR-менеджер', 'department': 'HR',
                'password': 'hr123', 'roles': ['HR']
            },

            # Руководители
            {
                'username': 'manager1', 'email': 'manager1@company.com',
                'first_name': 'Сергей', 'last_name': 'Кузнецов',
                'position': 'Директор по продажам', 'department': 'Продажи',
                'password': 'manager123', 'roles': ['Менеджер']
            },
            {
                'username': 'manager2', 'email': 'manager2@company.com',
                'first_name': 'Анна', 'last_name': 'Смирнова',
                'position': 'Руководитель отдела маркетинга', 'department': 'Маркетинг',
                'password': 'manager123', 'roles': ['Менеджер']
            },

            # Сотрудники
            {
                'username': 'employee1', 'email': 'employee1@company.com',
                'first_name': 'Иван', 'last_name': 'Федоров',
                'position': 'Менеджер по продажам', 'department': 'Продажи',
                'password': 'employee123', 'roles': ['Сотрудник']
            },
            {
                'username': 'employee2', 'email': 'employee2@company.com',
                'first_name': 'Мария', 'last_name': 'Васильева',
                'position': 'Маркетолог', 'department': 'Маркетинг',
                'password': 'employee123', 'roles': ['Сотрудник']
            },
            {
                'username': 'employee3', 'email': 'employee3@company.com',
                'first_name': 'Дмитрий', 'last_name': 'Николаев',
                'position': 'Аналитик', 'department': 'Аналитика',
                'password': 'employee123', 'roles': ['Сотрудник']
            },
            {
                'username': 'employee4', 'email': 'employee4@company.com',
                'first_name': 'Алиса', 'last_name': 'Козлова',
                'position': 'Дизайнер', 'department': 'Дизайн',
                'password': 'employee123', 'roles': ['Сотрудник']
            }
        ]

    def init_users_and_roles(self):
        """Инициализация пользователей и ролей"""
        # Создание ролей
        roles = {
            'Администратор': Role.objects.get_or_create(
                name='Администратор',
                defaults={'description': 'Полный доступ к системе'}
            )[0],
            'HR': Role.objects.get_or_create(
                name='HR',
                defaults={'description': 'Управление персоналом'}
            )[0],
            'Менеджер': Role.objects.get_or_create(
                name='Менеджер',
                defaults={'description': 'Управление командой'}
            )[0],
            'Сотрудник': Role.objects.get_or_create(
                name='Сотрудник',
                defaults={'description': 'Участие в опросах'}
            )[0]
        }

        # Создание пользователей
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
                logger.info(f"Создан пользователь: {user.username}")

            # Назначение ролей через UserRole
            for role_name in user_data.get('roles', []):
                if role_name in roles:
                    UserRole.objects.get_or_create(
                        user=user,
                        role=roles[role_name]
                    )
                    logger.debug(f"Назначена роль {role_name} пользователю {user.username}")

    def create_survey_template(self, config):
        try:
            # Получаем ВСЕХ администраторов через их роли
            admin_role = Role.objects.get(name='Администратор')
            admins = User.objects.filter(
                Q(is_superuser=True) |
                Q(userrole__role=admin_role)
            ).distinct()

            # Создаем шаблон без конкретного создателя
            template, created = SurveyTemplate.objects.get_or_create(
                name=config['name'],
                defaults={
                    'description': config['description'],
                    'created_by': None  # Убираем привязку к конкретному пользователю
                }
            )

            if created:
                # Создаем компетенции и вопросы только для нового шаблона
                for comp_data in config['competencies']:
                    comp = Competency.objects.create(
                        name=comp_data['name'],
                        description=comp_data['description'],
                        template=template
                    )

                    for q_data in comp_data['questions']:
                        if q_data['type'] == 'scale':
                            Question.objects.create(
                                text=q_data['text'],
                                competency=comp,
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
                                competency=comp,
                                answer_type='text'
                            )
                logger.info(f"Создан шаблон: {template.name}")
            else:
                logger.info(f"Шаблон {config['name']} уже существует, пропускаем создание")

            return template
        except Exception as e:
            logger.error(f"Ошибка: {str(e)}")
            raise

    def init_templates(self):
        """Инициализация шаблонов опросов с полными данными"""
        templates_config = [
            {
                'name': 'Оценка руководителя 360°',
                'description': 'Полная оценка управленческих компетенций',
                'competencies': [
                    {
                        'name': 'Лидерство',
                        'description': 'Способность вести команду к достижению целей',
                        'questions': [
                            # Существующие 3 вопроса
                            {'text': 'Приведите примеры эффективного разрешения конфликтов в команде', 'type': 'text'},
                            {'text': 'Оцените способность принимать сложные решения', 'type': 'scale'},
                            {'text': 'Насколько руководитель открыт для обратной связи?', 'type': 'scale'}
                        ]
                    },
                    {
                        'name': 'Стратегическое мышление',
                        'description': 'Способность видеть перспективу развития',
                        'questions': [
                            # Существующие 3 вопроса
                            {'text': 'Как руководитель анализирует рыночные тенденции?', 'type': 'text'},
                            {'text': 'Оцените качество долгосрочного планирования', 'type': 'scale'}
                        ]
                    },
                    # Новая компетенция
                    {
                        'name': 'Эффективность коммуникаций',
                        'description': 'Умение выстраивать диалог с командой',
                        'questions': [
                            {'text': 'Насколько четко руководитель доносит цели компании?', 'type': 'scale'},
                            {'text': 'Оцените регулярность и полезность командных встреч', 'type': 'scale'},
                            {'text': 'Примеры улучшений в коммуникациях за последний квартал', 'type': 'text'}
                        ]
                    },
                    {
                        'name': 'Управление изменениями',
                        'description': 'Реакция на организационные изменения',
                        'questions': [
                            {'text': 'Как руководитель внедряет изменения в команде?', 'type': 'text'},
                            {'text': 'Оцените гибкость в адаптации к новым процессам', 'type': 'scale'}
                        ]
                    }
                ]
            },
            {
                'name': 'Оценка сотрудника',
                'description': 'Регулярная оценка профессиональных качеств',
                'competencies': [
                    {
                        'name': 'Профессионализм',
                        'description': 'Уровень профессиональных знаний и навыков',
                        'questions': [
                            # Существующие 2 вопроса
                            {'text': 'Оцените способность работать без контроля', 'type': 'scale'},
                            {'text': 'Как сотрудник реагирует на стрессовые ситуации?', 'type': 'text'}
                        ]
                    },
                    {
                        'name': 'Коммуникация',
                        'description': 'Эффективность взаимодействия с коллегами',
                        'questions': [
                            # Существующие 2 вопроса
                            {'text': 'Оцените ясность постановки задач коллегам', 'type': 'scale'},
                            {'text': 'Примеры эффективного разрешения конфликтов', 'type': 'text'}
                        ]
                    },
                    # Новая компетенция
                    {
                        'name': 'Инновации',
                        'description': 'Стремление к улучшению процессов',
                        'questions': [
                            {'text': 'Оцените количество предложенных улучшений за квартал', 'type': 'scale'},
                            {'text': 'Приведите примеры успешных инициатив', 'type': 'text'}
                        ]
                    },
                    {
                        'name': 'Рабочая этика',
                        'description': 'Соблюдение корпоративных норм',
                        'questions': [
                            {'text': 'Оцените соблюдение дедлайнов', 'type': 'scale'},
                            {'text': 'Насколько сотрудник следует процедурам компании?', 'type': 'scale'},
                            {'text': 'Примеры ответственного подхода к задачам', 'type': 'text'}
                        ]
                    }
                ]
            },
            {
                'name': 'Адаптационный опрос',
                'description': 'Оценка прохождения испытательного срока',
                'competencies': [
                    {
                        'name': 'Обучение',
                        'description': 'Освоение новых навыков и технологий',
                        'questions': [
                            # Существующие 2 вопроса
                            {'text': 'Оцените скорость освоения инструментов', 'type': 'scale'},
                            {'text': 'Какие области требуют дополнительного обучения?', 'type': 'text'}
                        ]
                    },
                    {
                        'name': 'Интеграция',
                        'description': 'Вхождение в коллектив и корпоративную культуру',
                        'questions': [
                            # Существующие 2 вопроса
                            {'text': 'Оцените участие в корпоративных мероприятиях', 'type': 'scale'},
                            {'text': 'Примеры успешного взаимодействия с коллегами', 'type': 'text'}
                        ]
                    },
                    # Новая компетенция
                    {
                        'name': 'Производительность',
                        'description': 'Эффективность выполнения задач',
                        'questions': [
                            {'text': 'Оцените качество выполненных задач', 'type': 'scale'},
                            {'text': 'Соответствие результатов ожиданиям', 'type': 'scale'},
                            {'text': 'Какие задачи вызывали затруднения?', 'type': 'text'}
                        ]
                    },
                    {
                        'name': 'Профессиональный рост',
                        'description': 'Стремление к развитию',
                        'questions': [
                            {'text': 'Оцените активность в обучении', 'type': 'scale'},
                            {'text': 'Какие навыки планирует развивать?', 'type': 'text'}
                        ]
                    }
                ]
            }
        ]

        for config in templates_config:
            try:
                self.stdout.write(f"Создание шаблона: {config['name']}...")
                self.create_survey_template(config)
                self.stdout.write(self.style.SUCCESS(f"Шаблон {config['name']} создан"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Ошибка: {str(e)}"))

    def create_demo_survey(self):
        """Создание демо-опроса"""
        try:
            template = SurveyTemplate.objects.get(name='Оценка руководителя 360°')
            hr = User.objects.get(username='hr1')

            survey = Survey.objects.create(
                name='Демо-опрос 2024',
                template=template,
                start_date=date.today(),
                end_date=date.today() + timedelta(days=14),
                status='active',
                created_by=hr
            )

            respondent = Respondent.objects.create(
                survey=survey,
                user=User.objects.get(username='manager1'),
                manager=hr
            )

            Rater.objects.create(
                respondent=respondent,
                user=User.objects.get(username='employee1'),
                relationship_type='peer'
            )

            logger.info(f"Создан демо-опрос ID: {survey.id}")

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
            "HR: hr1/hr123\n"
            "Менеджер: manager1/manager123"
        ))