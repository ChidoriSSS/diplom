from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Survey, Respondent, Question, Response, SurveyTemplate, Rater
import logging
logger = logging.getLogger(__name__)
from django.forms import inlineformset_factory


User = get_user_model()


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
                'sort_order': 0,
                'scale_min': 1,
                'scale_max': 5
            })
        # Принудительно устанавливаем значения для шкалы, если тип - scale
        if self.instance.answer_type == 'scale' or self.data.get('answer_type') == 'scale':
            self.initial['scale_min'] = 1
            self.initial['scale_max'] = 5

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

