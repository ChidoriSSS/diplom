from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.serializers import json
from django.db import IntegrityError
from django.db.models import Q
from django.utils import timezone
from .models import Survey, Respondent, Question, Response, SurveyTemplate, Rater
import numpy
import logging
logger = logging.getLogger(__name__)
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class SurveyForm(forms.ModelForm):
    class Meta:
        model = Survey
        fields = ['template', 'name', 'description', 'start_date', 'end_date']
        widgets = {
            'template': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите название опроса'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Опишите цель опроса'
            }),
            'start_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'end_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
        }

    def __init__(self, *args, **kwargs):
        # Удаляем обработку admin_mode
        super().__init__(*args, **kwargs)
        self.fields['template'].queryset = SurveyTemplate.objects.filter(is_active=True)
        self.fields['template'].empty_label = "Выберите шаблон"

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date:
            if start_date < timezone.now().date():
                raise ValidationError("Дата начала не может быть в прошлом")
            if end_date <= start_date:
                raise ValidationError("Дата окончания должна быть позже даты начала")

        return cleaned_data

class RespondentForm(forms.ModelForm):
    class Meta:
        model = Respondent
        fields = ['user', 'manager']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-select'}),
            'manager': forms.Select(attrs={'class': 'form-select'}),
        }

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text', 'answer_type', 'scale_min', 'scale_max', 'is_required', 'competency']
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2
            }),
            'answer_type': forms.Select(attrs={'class': 'form-select'}),
            'scale_min': forms.NumberInput(attrs={'class': 'form-control'}),
            'scale_max': forms.NumberInput(attrs={'class': 'form-control'}),
            'competency': forms.Select(attrs={'class': 'form-select'}),
            'is_required': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Добавляем валидацию для числовых полей
        self.fields['scale_min'].min_value = 1
        self.fields['scale_max'].max_value = 10


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

class RaterAssignmentForm(forms.Form):
    raters = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'size': '8',
            'style': 'min-height: 200px;'
        })
    )
    relationship_type = forms.ChoiceField(
        choices=Rater.RELATIONSHIP_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        available_users = kwargs.pop('available_users', None)
        super().__init__(*args, **kwargs)
        if available_users:
            self.fields['raters'].queryset = available_users


class ScaleResponseForm(ResponseForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Проверяем наличие вопроса
        if not self.question:
            raise ValueError("Question is required for ScaleResponseForm")

        # Безопасное получение вариантов ответов
        default_choices = [
            ('1', '1 - Никогда'),
            ('2', '2 - Редко'),
            ('3', '3 - Иногда'),
            ('4', '4 - Часто'),
            ('5', '5 - Всегда')
        ]

        choices = getattr(self.question, 'scale_choices', None)
        if isinstance(choices, list) and len(choices) > 0:
            self.fields['answer_value'].choices = choices
        else:
            self.fields['answer_value'].choices = default_choices


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