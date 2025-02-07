from django.contrib import admin
from .models import User, Survey, Question, Option, Response, SurveyParticipant

admin.site.register(User)
admin.site.register(Survey)
admin.site.register(Question)
admin.site.register(Option)
admin.site.register(Response)
admin.site.register(SurveyParticipant)
