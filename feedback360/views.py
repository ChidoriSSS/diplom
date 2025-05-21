from django.db import transaction
from django.db.models import ProtectedError
from django.views.generic import (
    ListView, DetailView, CreateView,
    UpdateView, TemplateView, DeleteView
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from .models import Survey, Respondent, Question, User, Rater, SurveyTemplate
from .forms import SurveyForm, QuestionForm, QuestionFormSet, RespondentFormSet, SurveyTemplateForm
from django.contrib.auth.decorators import login_required
from .mixins import LeaderRequiredMixin, AdminRequiredMixin, user_has_admin_access
from .utils import copy_questions_from_template
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin




import logging
logger = logging.getLogger(__name__)


@login_required
def profile(request):
    return render(request, 'feedback360/profile.html', {
        'user': request.user
    })


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'feedback360/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_employee'] = self.request.user.is_employee
        return context


class SurveyCreateView(LeaderRequiredMixin, CreateView):
    model = Survey
    form_class = SurveyForm
    template_name = 'feedback360/survey_create.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['available_templates'] = SurveyTemplate.objects.filter(is_active=True)
        context['is_admin'] = user_has_admin_access(self.request.user)

        if self.request.POST:
            context['respondents_formset'] = RespondentFormSet(
                self.request.POST,
                prefix='respondents'
            )
            context['questions_formset'] = QuestionFormSet(
                self.request.POST,
                prefix='questions',
                queryset=Question.objects.none()
            )
        else:
            context['respondents_formset'] = RespondentFormSet(
                prefix='respondents',
                queryset=Respondent.objects.none()
            )
            context['questions_formset'] = QuestionFormSet(
                prefix='questions',
                queryset=Question.objects.none()
            )

        return context

    def form_valid(self, form):
        survey = form.save(commit=False)
        survey.created_by = self.request.user
        survey.save()

        # Обработка участников
        respondents_formset = self.get_context_data()['respondents_formset']
        if respondents_formset.is_valid():
            respondents = respondents_formset.save(commit=False)
            for respondent in respondents:
                respondent.survey = survey
                respondent.save()

        # Обработка вопросов
        questions_formset = self.get_context_data()['questions_formset']
        if questions_formset.is_valid():
            questions = questions_formset.save(commit=False)
            for idx, question in enumerate(questions, start=1):
                question.survey = survey
                question.sort_order = idx
                question.save()

        # Копирование из шаблона (если выбран)
        if survey.template:
            Question.copy_from_template(survey.template, survey)

        return super().form_valid(form)

    def get_success_url(self):
        return reverse('survey_detail', kwargs={'pk': self.object.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs



class SurveyListView(LoginRequiredMixin, ListView):
    model = Survey
    template_name = 'feedback360/survey_list.html'
    context_object_name = 'surveys'
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        if user_has_admin_access(user):
            return Survey.objects.all().order_by('-created_at')
        return Survey.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_admin'] = user_has_admin_access(self.request.user)
        return context


class SurveyDetailView(LoginRequiredMixin, DetailView):
    model = Survey
    template_name = 'feedback360/survey_detail.html'
    context_object_name = 'survey'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        survey = self.object

        # Для администраторов показываем всех пользователей кроме уже добавленных
        existing_users = survey.respondents.values_list('user_id', flat=True)
        context['available_users'] = User.objects.exclude(id__in=existing_users)

        # Добавляем флаг администратора в контекст
        context['is_admin'] = user_has_admin_access(self.request.user)

        return context



class QuestionCreateView(LoginRequiredMixin, CreateView):
    model = Question
    form_class = QuestionForm
    template_name = 'feedback360/question_create.html'

    def form_valid(self, form):
        survey = get_object_or_404(Survey, pk=self.kwargs['pk'])
        form.instance.survey = survey
        messages.success(self.request, "Вопрос успешно добавлен!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('survey_detail', kwargs={'pk': self.kwargs['pk']})



def custom_404_view(request, exception):
    return render(request, 'feedback360/404.html', status=404)

class LeaderSurveyCreateView(LeaderRequiredMixin, CreateView):
    model = Survey
    form_class = SurveyForm
    template_name = 'feedback360/survey_create.html'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        copy_questions_from_template(self.object)
        return response

class LeaderSurveyUpdateView(LeaderRequiredMixin, UpdateView):
    model = Survey
    form_class = SurveyForm
    template_name = 'feedback360/survey_update.html'

    def get_queryset(self):
        return super().get_queryset().filter(created_by=self.request.user)


def get_template_questions(request, template_id):
    try:
        template = SurveyTemplate.objects.get(pk=template_id)
        questions = template.template_questions.order_by('sort_order').values(
            'id', 'text', 'answer_type', 'sort_order'
        )
        return JsonResponse({
            'status': 'success',
            'questions': list(questions)
        })
    except SurveyTemplate.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Шаблон не найден'
        }, status=404)



class TemplateListView(AdminRequiredMixin, ListView):
    model = SurveyTemplate
    template_name = 'feedback360/template_list.html'
    context_object_name = 'templates'

    def get_queryset(self):
        return SurveyTemplate.objects.all().prefetch_related('template_questions')


class TemplateDeleteView(AdminRequiredMixin, DeleteView):
    model = SurveyTemplate
    template_name = 'feedback360/surveytemplate_confirm_delete.html'
    success_url = reverse_lazy('template_list')

    def delete(self, request, *args, **kwargs):
        try:
            return super().delete(request, *args, **kwargs)
        except ProtectedError:
            messages.error(request, "Невозможно удалить шаблон, так как он используется в опросах")
            return redirect('template_list')


class TemplateCreateView(AdminRequiredMixin, CreateView):
    model = SurveyTemplate
    form_class = SurveyTemplateForm
    template_name = 'feedback360/template_create.html'
    success_url = reverse_lazy('template_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = QuestionFormSet(self.request.POST)
        else:
            context['formset'] = QuestionFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data(form=form)
        formset = context['formset']

        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            return super().form_valid(form)
        else:
            return self.render_to_response(context)


class TemplateUpdateView(AdminRequiredMixin, UpdateView):
    model = SurveyTemplate
    form_class = SurveyTemplateForm
    template_name = 'feedback360/template_edit.html'
    success_url = reverse_lazy('template_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = QuestionFormSet(
                self.request.POST,
                instance=self.object,
                queryset=self.object.template_questions.order_by('sort_order'),
                prefix='template_questions'
            )
        else:
            context['formset'] = QuestionFormSet(
                self.request.POST or None,
                instance=self.object,
                prefix='template_questions'
            )
        return context

    @transaction.atomic
    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']

        if not formset.is_valid():
            return self.form_invalid(form)

        self.object = form.save()

        # Получаем все существующие вопросы
        existing_questions = list(self.object.template_questions.all())
        questions_to_keep = []

        # Обрабатываем каждую форму
        for form in formset:
            if form.cleaned_data.get('DELETE'):
                # Удаляем помеченные вопросы
                if form.instance.pk:
                    form.instance.delete()
            else:
                instance = form.save(commit=False)
                instance.template = self.object
                questions_to_keep.append(instance)

        # Обновляем порядок вопросов
        for i, question in enumerate(questions_to_keep):
            question.sort_order = i + 1
            question.save()

        messages.success(self.request, "Шаблон успешно обновлён!")
        return redirect('template_list')

class QuestionDeleteView(AdminRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            question = Question.objects.get(
                pk=kwargs['question_pk'],
                template_id=kwargs['template_pk']
            )
            question.delete()
            return JsonResponse({'status': 'success'})
        except Question.DoesNotExist:
            return JsonResponse(
                {'status': 'error', 'message': 'Вопрос не найден'},
                status=404
            )
        except Exception as e:
            return JsonResponse(
                {'status': 'error', 'message': str(e)},
                status=500
            )