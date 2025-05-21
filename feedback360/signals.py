from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.urls import reverse

from survey360 import settings
from .models import Survey
from .utils import send_survey_invitation

@receiver(post_save, sender=Survey)
def handle_survey_status_change(sender, instance, **kwargs):
    if instance.status == 'active' and instance.pk:
        instance.send_invitations()

