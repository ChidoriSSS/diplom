from django.db import models, IntegrityError
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db.models import Max
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator


class User(AbstractUser):
    position = models.CharField(max_length=100, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)

    def get_display_name(self):
        return f"{self.get_full_name()} ({self.position})" if self.position else self.get_full_name()

    @property
    def is_leader(self):
        return self.userrole_set.filter(role__name='Руководитель').exists()


class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'role')


class Question(models.Model):
    survey = models.ForeignKey('Survey',on_delete=models.CASCADE,related_name='questions',null=True,blank=True)

    ANSWER_TYPES = (
        ('scale', 'Шкала'),
        ('text', 'Текст'),
    )

    SCALE_CHOICES = [
        ('1', '1 - Никогда'),
        ('2', '2 - Редко'),
        ('3', '3 - Иногда'),
        ('4', '4 - Часто'),
        ('5', '5 - Очень часто'),
    ]

    template = models.ForeignKey('SurveyTemplate',on_delete=models.CASCADE,related_name='template_questions', null=True,blank=True)
    scale_choices = models.JSONField(default=list,blank=True,null=True,help_text="Формат: [['значение', 'описание'], ...]")
    text = models.TextField(verbose_name='Текст вопроса', blank=False, null=False, help_text="Обязательное поле")
    answer_type = models.CharField(max_length=50,choices=ANSWER_TYPES,verbose_name='Тип ответа',default='scale')
    scale_min = models.IntegerField(null=True, blank=True, default=1)
    scale_max = models.IntegerField(null=True, blank=True, default=5)
    is_required = models.BooleanField(default=True, verbose_name='Обязательный вопрос')
    sort_order = models.PositiveIntegerField(
        default=0,
        verbose_name='Порядок сортировки',
        db_index=True,
    )

    class Meta:
        ordering = ['sort_order']
        unique_together = ('template', 'sort_order')

    def save(self, *args, **kwargs):
        # Для новых вопросов без указанного порядка
        if not self.pk and self.sort_order == 0:
            max_order = Question.objects.filter(
                template=self.template
            ).aggregate(Max('sort_order'))['sort_order__max'] or 0
            self.sort_order = max_order + 1

        # Для scale вопросов устанавливаем значения по умолчанию
        if self.answer_type == 'scale':
            self.scale_min = 1
            self.scale_max = 5

        super().save(*args, **kwargs)

    def clean(self):
        if self.answer_type == 'scale':
            self.scale_min = 1
            self.scale_max = 5

    class Meta:
        verbose_name = 'Вопрос'
        verbose_name_plural = 'Вопросы'
        ordering = ['sort_order']

    def __str__(self):
        return f"{self.text[:50]}..."

    @classmethod
    def copy_from_template(cls, template, survey):
        return cls.objects.bulk_create([
            cls(
                text=question.text,
                answer_type=question.answer_type,
                survey=survey,
                is_required=question.is_required,
                sort_order=question.sort_order,
                scale_min=1,
                scale_max=5,
                scale_choices=question.scale_choices
            )
            for question in template.template_questions.all()
        ])


class SurveyTemplate(models.Model):
    name = models.CharField('Название шаблона', max_length=255)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(
        'Активен',
        default=True,
    )

    def __str__(self):
        return f"{self.name} {'(активен)' if self.is_active else '(неактивен)'}"

    class Meta:
        verbose_name = _('Шаблон опроса')
        verbose_name_plural = _('Шаблоны опросов')
        permissions = [
            ('can_manage_templates', 'Может управлять шаблонами'),
        ]

    def get_absolute_url(self):
        return reverse('template_edit', args=[str(self.id)])

    def can_edit(self, user):
        return True

    def get_competencies(self):
        return self.template_competencies.all().prefetch_related('question_set')


class Survey(models.Model):
    name = models.CharField(_('Название опроса'), max_length=255)
    description = models.TextField(_('Описание'), blank=True)
    template = models.ForeignKey(
        SurveyTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Основан на шаблоне')
    )
    start_date = models.DateField(_('Дата начала'))
    end_date = models.DateField(_('Дата окончания'))
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_('Создатель')
    )
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)

    STATUS_CHOICES = [
        ('draft', _('Черновик')),
        ('active', _('Активен')),
        ('completed', _('Завершен')),
    ]
    status = models.CharField(
        _('Статус'),
        max_length=10,
        choices=STATUS_CHOICES,
        default='draft'
    )

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
            MinValueValidator(1),
            MaxValueValidator(5)
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


@receiver(post_save, sender=Survey)
def handle_survey_status_change(sender, instance, **kwargs):
    if instance.status == 'active' and instance.pk:
        instance.send_invitations()

