from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('creator', 'Creator'),
        ('participant', 'Participant'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username

class Survey(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='surveys')

    def __str__(self):
        return self.title

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

class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    option_text = models.CharField(max_length=100)

    def __str__(self):
        return self.option_text

class Response(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='responses')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='responses')
    answer_text = models.TextField()

    def __str__(self):
        return f"Response by {self.user.username} to {self.question.question_text}"

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