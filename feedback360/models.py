from django.core.exceptions import ValidationError
from django.db import models, IntegrityError
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    position = models.CharField(max_length=100, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Роль'
        verbose_name_plural = 'Роли'

    def __str__(self):
        return self.name


class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'role')
        verbose_name = 'Роль пользователя'
        verbose_name_plural = 'Роли пользователей'


class SurveyTemplate(models.Model):
    name = models.CharField(_('Название шаблона'), max_length=255)
    description = models.TextField(_('Описание'), blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Создатель'),
        editable=False  # Запрещаем редактирование в админке
    )
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    is_active = models.BooleanField(_('Активен'), default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('Шаблон опроса')
        verbose_name_plural = _('Шаблоны опросов')

    class Meta:
        permissions = [
            ('view_all_templates', 'Можно просмотреть все шаблоны опросов'),
        ]

class Competency(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    template = models.ForeignKey(SurveyTemplate, on_delete=models.CASCADE, related_name='competencies')
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    sort_order = models.IntegerField(blank=True, null=True, default=0)


    class Meta:
        verbose_name = 'Компетенция'
        verbose_name_plural = 'Компетенции'
        ordering = ['sort_order']

    def __str__(self):
        return f"{self.name} ({self.template.name})"


class Question(models.Model):
    ANSWER_TYPES = (
        ('scale', 'Шкала'),
        ('text', 'Текст'),
        ('multiple', 'Множественный выбор'),
        ('list', 'Нумерованный список'),
    )

    SCALE_CHOICES = [
        ('1', '1 - Никогда'),
        ('2', '2 - Редко'),
        ('3', '3 - Иногда'),
        ('4', '4 - Часто'),
        ('5', '5 - Всегда'),
    ]

    scale_choices = models.JSONField(
        default=list,
        blank=True,
        null=True,
        help_text="Формат: [['значение', 'описание'], ...]"
    )

    text = models.TextField()
    competency = models.ForeignKey(Competency, on_delete=models.CASCADE, related_name='questions')
    answer_type = models.CharField(max_length=50, choices=ANSWER_TYPES)
    scale_min = models.IntegerField(null=True, blank=True,default=1)
    scale_max = models.IntegerField(null=True, blank=True,default=5)
    is_required = models.BooleanField(default=True)
    sort_order = models.IntegerField(blank=True, null=True, default=0)

    def clean(self):
        if self.answer_type == 'scale' and (self.scale_min is None or self.scale_max is None):
            raise ValidationError("Для вопросов со шкалой укажите scale_min и scale_max")
        elif self.answer_type != 'scale' and (self.scale_min or self.scale_max):
            raise ValidationError("Параметры шкалы должны быть пустыми для этого типа вопроса")

    class Meta:
        verbose_name = 'Вопрос'
        verbose_name_plural = 'Вопросы'
        ordering = ['competency__sort_order', 'sort_order']

    def __str__(self):
        return f"{self.text[:50]}... ({self.competency.name})"




class Survey(models.Model):
    name = models.CharField(_('Название опроса'), max_length=255)
    description = models.TextField(_('Описание'), blank=True)
    template = models.ForeignKey(SurveyTemplate, on_delete=models.PROTECT, verbose_name=_('Шаблон'))
    start_date = models.DateField(_('Дата начала'))
    end_date = models.DateField(_('Дата окончания'))
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('Создатель'))
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)


    def get_user_progress(self, user):
        total_questions = Question.objects.filter(competency__template=self.template).count()
        answered = Response.objects.filter(
            rater__user=user,
            rater__respondent__survey=self
        ).count()
        return min(100, round((answered / total_questions) * 100)) if total_questions > 0 else 0

    STATUS_CHOICES = [
        ('draft', _('Черновик')),
        ('active', _('Активен')),
        ('completed', _('Завершен')),
    ]
    status = models.CharField(_('Статус'), max_length=10, choices=STATUS_CHOICES, default='draft')

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    class Meta:
        verbose_name = _('Опрос')
        verbose_name_plural = _('Опросы')
        ordering = ['-created_at']


class RaterGroup(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Группа оценивающих'
        verbose_name_plural = 'Группы оценивающих'

    def __str__(self):
        return self.name


class Respondent(models.Model):
    STATUS_CHOICES = (
        ('not_started', 'Не начат'),
        ('in_progress', 'В процессе'),
        ('completed', 'Завершен'),
    )

    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='respondents')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='respondent_surveys')
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='managed_respondents')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='not_started')
    completion_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = 'Оцениваемый'
        verbose_name_plural = 'Оцениваемые'
        unique_together = ('survey', 'user')

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.survey.name})"


class Rater(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Ожидает'),
        ('started', 'Начал'),
        ('completed', 'Завершил'),
    )
    RELATIONSHIP_TYPES = (
        ('self', 'Сам себе'),
        ('manager', 'Руководитель'),
        ('peer', 'Коллега'),
        ('subordinate', 'Подчиненный'),
        ('other', 'Другое'),
    )

    respondent = models.ForeignKey(Respondent, on_delete=models.CASCADE, related_name='raters')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assessments')
    rater_group = models.ForeignKey(RaterGroup, on_delete=models.SET_NULL, null=True, blank=True)
    relationship_type = models.CharField(max_length=100, choices=RELATIONSHIP_TYPES)
    token = models.CharField(max_length=255, unique=True, blank=True, null=True)
    invitation_sent = models.BooleanField(default=False)
    invitation_date = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    completed_at = models.DateTimeField(blank=True, null=True)

    @property
    def days_remaining(self):
        from django.utils.timezone import now
        return (self.respondent.survey.end_date - now().date()).days

    class Meta:
        verbose_name = 'Оценивающий'
        verbose_name_plural = 'Оценивающие'
        unique_together = ('respondent', 'user')

    def __str__(self):
        return f"{self.user.get_full_name()} оценивает {self.respondent.user.get_full_name()}"


class Response(models.Model):
    rater = models.ForeignKey(Rater, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='responses')
    answer_value = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        blank=True,
        null=True,
        validators=[
            MinValueValidator(0.5),
            MaxValueValidator(10)
        ]
    )
    answer_text = models.TextField(blank=True, null=True)
    answered_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if not self.question_id:
            raise ValidationError("Ответ должен быть привязан к вопросу")

        try:
            question = Question.objects.get(id=self.question_id)
        except Question.DoesNotExist:
            raise ValidationError("Указанный вопрос не существует")

        if question.answer_type == 'scale' and not self.answer_value:
            raise ValidationError("Выберите значение шкалы")

    class Meta:
        unique_together = ('rater', 'question')
        verbose_name = 'Ответ'
        verbose_name_plural = 'Ответы'

    def __str__(self):
        return f"Ответ {self.rater.user.get_full_name()} на вопрос {self.question.id}"

    def save(self, *args, **kwargs):
        # Проверяем уникальность перед сохранением
        if self.pk is None:  # Только для новых объектов
            if Response.objects.filter(
                    rater=self.rater,
                    question=self.question
            ).exists():
                raise IntegrityError("Ответ уже существует")
        super().save(*args, **kwargs)


class Report(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='reports')
    respondent = models.ForeignKey(Respondent, on_delete=models.CASCADE, related_name='reports')
    report_data = models.JSONField()
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='generated_reports')

    class Meta:
        verbose_name = 'Отчет'
        verbose_name_plural = 'Отчеты'

    def __str__(self):
        return f"Отчет по {self.respondent.user.get_full_name()} ({self.survey.name})"

    def generate_report_data(self):
        """Автоматически генерирует данные отчета"""
        from django.db.models import Avg
        responses = Response.objects.filter(rater__respondent=self.respondent)

        # Преобразуем Decimal в float
        avg_score = responses.aggregate(Avg('answer_value'))['answer_value__avg'] or 0
        if avg_score:
            avg_score = float(round(avg_score, 1))

        # Формируем структуру отчета с сериализуемыми типами
        self.report_data = {
            'summary': {
                'average_score': avg_score,
                'total_questions': responses.count(),
                'answered_questions': responses.exclude(answer_value__isnull=True).count()
            },
            'details': [
                {
                    'question': response.question.text,
                    'answer': float(response.answer_value) if response.answer_value else response.answer_text
                }
                for response in responses
            ]
        }
        self.save()

@receiver(post_save, sender=Respondent)
def create_report(sender, instance, created, **kwargs):
    if created:
        report = Report.objects.create(
            respondent=instance,
            survey=instance.survey,
            report_data={},  # Инициализация пустым словарем
            generated_by=instance.survey.created_by
        )
        # Отложенная генерация данных
        report.generate_report_data()