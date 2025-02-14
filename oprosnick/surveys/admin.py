from django.contrib import admin
from .models import Survey, Question, Option, Response, SurveyParticipant

@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'created_at')

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'survey', 'question_type')

@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ('option_text', 'question')

@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ('question', 'user', 'answer_text')

@admin.register(SurveyParticipant)
class SurveyParticipantAdmin(admin.ModelAdmin):
    list_display = ('survey', 'user', 'status')
