from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission


class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('creator', 'Creator'),
        ('participant', 'Participant'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    # Исправляем конфликт с related_name
    groups = models.ManyToManyField(
        Group,
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name="surveys_user_groups"  # Уникальное имя
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="surveys_user_permissions"  # Уникальное имя
    )

    def __str__(self):
        return self.username

# Модель опроса
class Survey(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='surveys')

    def __str__(self):
        return self.title

# Модель вопроса
class Question(models.Model):
    QUESTION_TYPE_CHOICES = [
        ('singlechoice', 'Single Choice'),
        ('multiplechoice', 'Multiple Choice'),
        ('text', 'Text'),
    ]

    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES)

    def __str__(self):
        return self.question_text

# Модель варианта ответа
class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    option_text = models.CharField(max_length=100)

    def __str__(self):
        return self.option_text

# Модель ответа
class Response(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='responses')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='responses')
    answer_text = models.TextField()

    def __str__(self):
        return f"Response by {self.user.username} to {self.question.question_text}"

# Модель участника опроса
class SurveyParticipant(models.Model):
    STATUS_CHOICES = [
        ('invited', 'Invited'),
        ('completed', 'Completed'),
    ]

    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='survey_participants')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    def __str__(self):
        return f"{self.user.username} - {self.survey.title} - {self.status}"