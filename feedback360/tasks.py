from celery import shared_task
from .models import Survey
from .utils import send_survey_invitation

@shared_task
def send_survey_emails(survey_id):
    survey = Survey.objects.get(id=survey_id)
    for respondent in survey.respondents.all():
        send_survey_invitation(survey, respondent.user)