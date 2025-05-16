from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.urls import reverse

from survey360 import settings
from .models import Survey, AccessRequest
from .utils import send_survey_invitation

@receiver(post_save, sender=Survey)
def handle_survey_status_change(sender, instance, **kwargs):
    if instance.status == 'active' and instance.pk:
        instance.send_invitations()

@receiver(post_save, sender=AccessRequest)
def handle_access_request(sender, instance, created, **kwargs):
    if created:
        # Отправка email-уведомления администратору
        subject = f'Новый запрос прав доступа от {instance.requester}'
        message = render_to_string('feedback360/email/access_request_notification.html', {
            'admin': instance.admin,
            'requester': instance.requester,
            'link': reverse('access_request_detail', args=[instance.id])
        })
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [instance.admin.email],
            html_message=message
        )