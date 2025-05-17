from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.serializers import json
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import IntegrityError
from django.db.models import Q
from django.utils import timezone
from .models import Survey, Respondent, Question, Response, SurveyTemplate, Rater, Notification, AccessRequest
import numpy
import logging
logger = logging.getLogger(__name__)
from django.utils.translation import gettext_lazy as _
from django.forms import inlineformset_factory


User = get_user_model()


class AccessRequestForm(forms.ModelForm):
    class Meta:
        model = AccessRequest
        fields = ['admin', 'comment']  # Теперь поле comment существует
        widgets = {
            'admin': forms.Select(attrs={'class': 'form-select'}),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Опишите цели оценки'
            })
        }

class NotificationForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = ['message', 'link']

class SurveyForm(forms.ModelForm):
    class Meta:
        model = Survey
        fields = ['name', 'start_date', 'end_date', 'template']
        widgets = {
            'template': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'start_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'min': timezone.now().date().isoformat()
            }),
            'end_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.user and not self.user.is_superuser:
            self.fields['template'].queryset = SurveyTemplate.objects.filter(is_active=True)

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date and start_date > end_date:
            raise ValidationError("Дата окончания должна быть позже даты начала")

        return cleaned_data


class RespondentForm(forms.ModelForm):
    class Meta:
        model = Respondent
        fields = '__all__'
        widgets = {
            'user': forms.Select(attrs={'autocomplete': 'off'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].queryset = User.objects.all()
        self.fields['user'].label_from_instance = lambda obj: obj.get_display_name()

class CustomDeleteCheckbox(forms.CheckboxInput):
    template_name = 'feedback360/custom_delete_checkbox.html'

class QuestionForm(forms.ModelForm):
    DELETE = forms.BooleanField(
        required=False,
        widget=forms.HiddenInput(attrs={'class': 'delete-flag'}))
    class Meta:
        model = Question
        fields = ['text', 'answer_type', 'sort_order', 'scale_min', 'scale_max']
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Введите текст вопроса'
            }),
            'answer_type': forms.Select(attrs={'class': 'form-select'}),
            'sort_order': forms.HiddenInput(),
            'scale_min': forms.HiddenInput(),
            'scale_max': forms.HiddenInput()
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.initial.update({
                'sort_order': 0,  # Временное значение (перезапишется во View)
                'scale_min': 1,
                'scale_max': 5
            })

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('DELETE'):
            # Пропускаем остальные проверки для удаляемых вопросов
            return cleaned_data


QuestionFormSet = inlineformset_factory(
    SurveyTemplate,
    Question,
    form=QuestionForm,
    fields=('text', 'answer_type', 'sort_order', 'scale_min', 'scale_max'),
    extra=0,
    can_delete=True,
    widgets={
        'sort_order': forms.HiddenInput(),
        'scale_min': forms.HiddenInput(),
        'scale_max': forms.HiddenInput()
    }
)

RespondentFormSet = inlineformset_factory(
    Survey,
    Respondent,
    form=RespondentForm,
    extra=1,
    can_delete=True,
    fields=('user',),
    widgets={
        'user': forms.Select(attrs={'class': 'form-select'}),
        'DELETE': forms.HiddenInput()
    }
)


def clean_sort_order(self):
    data = self.cleaned_data.get('sort_order')
    if data and data < 1:
        raise ValidationError("Порядковый номер не может быть меньше 1")
    return data



class SurveyCreationForm(forms.ModelForm):
    class Meta:
        model = Survey
        fields = ['name', 'template', 'start_date', 'end_date']  # Используем существующие поля
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'template': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }


class ResponseForm(forms.ModelForm):
    question = forms.ModelChoiceField(
        queryset=Question.objects.all(),
        widget=forms.HiddenInput(),
        label=_('Вопрос'),
        error_messages={'required': _('Требуется привязка к вопросу')}
    )

    class Meta:
        model = Response
        fields = ['question', 'answer_value', 'answer_text']
        labels = {
            'answer_text': _('Комментарий (необязательно)')
        }

    def __init__(self, *args, **kwargs):
        self.question = kwargs.pop('question', None)
        self.rater = kwargs.pop('rater', None)
        super().__init__(*args, **kwargs)

        if self.question:
            self.fields['question'].initial = self.question.id
            self.fields['question'].widget = forms.HiddenInput()

        # Безопасная проверка наличия полей
        if 'answer_value' in self.fields:
            self.fields['answer_value'].required = False

        if 'answer_text' in self.fields:
            self.fields['answer_text'].required = False

    def clean(self):
        cleaned_data = super().clean()
        if self.data.get('direction') == 'back':
            return cleaned_data

        question = cleaned_data.get('question')
        if not question or not question.is_required:
            return cleaned_data

        # Удаляем все предыдущие ошибки
        self.errors.clear()

        error_msg = None
        if question.answer_type == 'text' and not cleaned_data.get('answer_text'):
            error_msg = "Требуется текстовый ответ"
        elif question.answer_type in ['scale', 'multiple'] and not cleaned_data.get('answer_value'):
            error_msg = "Необходимо выбрать вариант ответа"

        if error_msg:
            self.add_error(None, error_msg)  # Только в non_field_errors

        return cleaned_data

    def save(self, commit=True):
        # Всегда сохраняем ответ, даже при переходе назад
        instance = super().save(commit=False)
        instance.rater = self.rater
        instance.question = self.question

        if commit:
            try:
                instance.save()
            except IntegrityError:
                existing = Response.objects.get(
                    rater=self.rater,
                    question=self.question
                )
                existing.answer_value = instance.answer_value
                existing.answer_text = instance.answer_text
                existing.save()
                return existing

        return instance


class ScaleResponseForm(ResponseForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Принудительная установка допустимого диапазона
        self.fields['answer_value'] = forms.IntegerField(
            widget=forms.NumberInput(attrs={
                'min': 1,
                'max': 5,
                'step': 1
            }),
            validators=[
                MinValueValidator(1),
                MaxValueValidator(5)
            ]
        )


class TextResponseForm(ResponseForm):
    class Meta:
        model = Response
        fields = ['question', 'answer_text']  # Явно указываем используемые поля

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['answer_text'].widget = forms.Textarea(attrs={'rows': 4})

        # Делаем поле обязательным если вопрос требует этого
        if self.question and self.question.is_required:
            self.fields['answer_text'].required = True

    def clean_answer_text(self):  # Правильное имя метода для валидации
        data = self.cleaned_data.get('answer_text', '')

        if not data:  # Если поле пустое, пропускаем валидацию (required проверяется отдельно)
            return data

        if data.isdigit():
            raise ValidationError("Требуется текстовый ответ, а не только цифры")

        if len(data) < 10:
            raise ValidationError("Ответ должен содержать минимум 10 символов")

        return data

class MultipleChoiceResponseForm(ResponseForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        question = self.question
        self.fields['answer_value'] = forms.MultipleChoiceField(
            choices=question.get_choices(),
            widget=forms.CheckboxSelectMultiple,
            required=question.is_required
        )

        # Устанавливаем initial данные
        if self.instance and self.instance.answer_value:
            self.fields['answer_value'].initial = self.instance.answer_value.split(',')

    def save(self, commit=True):
        response = super().save(commit=False)
        answer_value = ','.join(self.cleaned_data['answer_value'])
        response.answer_value = answer_value
        if commit:
            response.save()
        return response


class ListResponseForm(forms.ModelForm):
    items = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Введите каждый пункт с новой строки'
        }),
        help_text="Пример:\n1. Первый пункт\n2. Второй пункт",
        required=True
    )

    class Meta:
        model = Response
        fields = ['answer_text']  # Используем существующее поле модели

    def clean_items(self):
        data = self.cleaned_data['items']
        items = [item.strip() for item in data.split('\n') if item.strip()]

        if len(items) < 2:
            raise ValidationError("Должно быть не менее 2 пунктов")
        if all(item.isdigit() for item in items):
            raise ValidationError("Пункты не могут состоять только из цифр")

        # Сохраняем как текст с разделителем
        return '\n'.join(items)

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Сохраняем обработанные данные в answer_text
        instance.answer_text = self.cleaned_data['items']
        if commit:
            instance.save()
        return instance

class SurveyTemplateForm(forms.ModelForm):
    class Meta:
        model = SurveyTemplate
        fields = ['name', 'is_active']
        labels = {
            'name': 'Название шаблона',
            'is_active': 'Активен'
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

