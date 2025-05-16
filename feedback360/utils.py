from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Survey, Question


def copy_questions_from_template(survey):
    template = survey.template
    if not template:
        return

    # Создаем независимые копии вопросов
    for template_question in template.template_questions.all():
        Question.objects.create(
            survey=survey,
            text=template_question.text,
            answer_type=template_question.answer_type,
            scale_min=template_question.scale_min,
            scale_max=template_question.scale_max,
            sort_order=template_question.sort_order
        )


def send_survey_invitation(survey, user):
    subject = f'Приглашение к участию в опросе: {survey.name}'
    message = render_to_string('feedback360/email/survey_invitation.html', {
        'user': user,
        'survey': survey,
        'start_date': survey.start_date,
        'end_date': survey.end_date
    })
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
        html_message=message
    )


def copy_template_to_survey(survey):
    if not survey.template:
        return

    # Копируем вопросы напрямую без компетенций
    for question in survey.template.template_questions.all():
        Question.objects.create(
            text=question.text,
            survey=survey,
            answer_type=question.answer_type,
            scale_min=question.scale_min,
            scale_max=question.scale_max,
            is_required=question.is_required,
            sort_order=question.sort_order
        )


def send_access_notification(admin, requester):
    message = render_to_string('feedback360/email/access_request_notification.html', {
        'admin': admin,
        'requester': requester
    })
    send_mail(
        f'Запрос прав доступа от {requester.get_full_name()}',
        message,
        settings.DEFAULT_FROM_EMAIL,
        [admin.email],
        html_message=message
    )