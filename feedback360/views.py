from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import ProtectedError, Q, Max
from django.forms import inlineformset_factory
from django.views import View
from django.views.generic import (
    ListView, DetailView, CreateView,
    UpdateView, TemplateView, DeleteView
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.utils import timezone

from . import forms
from .models import Survey, Respondent, Question, Response, User, Rater, SurveyTemplate, \
    Notification, UserRole, Role, AccessRequest
from .forms import SurveyForm, QuestionForm, ResponseForm, TextResponseForm, \
    MultipleChoiceResponseForm, ScaleResponseForm, ListResponseForm, QuestionFormSet, RespondentFormSet, \
    AccessRequestForm, SurveyTemplateForm
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.decorators import login_required
from .mixins import LeaderRequiredMixin, AdminRequiredMixin, user_has_admin_access, LeaderAccessMixin
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
        today = timezone.now().date()
        user = self.request.user
        context['is_employee'] = user.is_employee

        # Фильтры
        category = self.request.GET.get('category')
        sort_by = self.request.GET.get('sort', 'deadline')

        # Активные опросы
        active_surveys = Survey.objects.filter(
            respondents__user=user,
            start_date__lte=today,
            end_date__gte=today,
            status='active'
        ).distinct()

        # Добавляем дополнительные данные
        for survey in active_surveys:
            # Прогресс пользователя
            survey.user_progress = survey.get_user_progress(user)
            # Категории компетенций


        # Фильтрация по категории
        if category:
            active_surveys = [s for s in active_surveys if category in s.categories]

        # Сортировка
        if sort_by == 'progress':
            active_surveys = sorted(active_surveys,
                                  key=lambda s: s.user_progress,
                                  reverse=True)
        else:
            active_surveys = sorted(active_surveys,
                                   key=lambda s: s.end_date)

        # Ожидающие оценки
        pending_raters = Rater.objects.filter(
            user=user,
            status='pending',
            respondent__survey__end_date__gte=today
        ).select_related('respondent__survey')

        context.update({
            'active_surveys': active_surveys,
            'total_active': len(active_surveys),
            'surveys_to_complete': pending_raters.order_by('respondent__survey__end_date'),
            'total_pending': pending_raters.count(),
            'categories': [] ,
            'selected_category': category,
            'sort_mode': sort_by
        })
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


class SurveyQuestionsEditView(UpdateView):
    model = Survey
    template_name = 'feedback360/survey_questions_edit.html'
    fields = []

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def post(self, request, *args, **kwargs):
        survey = self.get_object()


        for key, value in request.POST.items():
            if key.startswith('question_'):
                q_id = key.split('_')[1]
                try:
                    question = Question.objects.get(id=q_id, survey=survey)
                    question.text = value
                    question.save()
                except Question.DoesNotExist:
                    pass


        new_questions = request.POST.getlist('new_questions[]')
        for q_text in new_questions:
            if q_text.strip():
                Question.objects.create(
                    text=q_text.strip(),
                    competency=survey.survey_competencies.first(),
                    answer_type='scale',
                    sort_order=999
                )

        return redirect('survey_detail', pk=survey.pk)



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


class ResponseCreateView(LoginRequiredMixin, CreateView):
    model = Response
    template_name = 'feedback360/response_form.html'
    form_class = ResponseForm
    fields = []

    def dispatch(self, request, *args, **kwargs):
        import logging
        logger = logging.getLogger(__name__)

        try:
            # Инициализация основных объектов
            self.rater = get_object_or_404(
                Rater,
                pk=kwargs['rater_id'],
                user=request.user,
                status__in=['pending', 'started']
            )
            self.survey = self.rater.respondent.survey

            # Инициализация сессионных ключей (ДОБАВЛЕНО)
            self.session_key = f'survey_{self.survey.id}_questions_order'
            self.full_list_key = f'survey_{self.survey.id}_full_questions'

            # Инициализация порядка вопросов
            if not request.session.get(self.session_key):
                questions = Question.objects.filter(
                    competency__template=self.survey.template
                ).order_by('competency__sort_order', 'sort_order').values_list('id', flat=True)
                request.session[self.session_key] = list(questions)
                request.session[self.full_list_key] = list(questions)
                request.session.modified = True

            # Получаем список всех вопросов (ИСПРАВЛЕНО)
            self.full_question_ids = request.session[self.full_list_key]
            self.total_questions = len(self.full_question_ids)

            # Сбрасываем сессию при начале нового опроса (ПЕРЕМЕЩЕНО ВНИЗ)
            self._init_session_data(request)

            # Обработка параметра запроса
            self.current_global_index = self._get_current_index(request)

            # Получаем текущий вопрос
            self.current_question = get_object_or_404(
                Question,
                id=self.full_question_ids[self.current_global_index]
            )

        except Exception as e:
            logger.error(f"Critical error: {str(e)}", exc_info=True)
            messages.error(request, "Произошла внутренняя ошибка")
            return redirect('dashboard')

        return super().dispatch(request, *args, **kwargs)

    def _init_session_data(self, request):
        """Инициализация сессионных данных для текущего опроса"""
        # Отдельный ключ для индекса (ИЗМЕНЕНО)
        self.index_session_key = f'survey_{self.survey.id}_current_index'

        # Сбрасываем индекс при первом обращении к опросу
        if f'survey_{self.survey.id}_initialized' not in request.session:
            request.session[self.index_session_key] = 0
            request.session[f'survey_{self.survey.id}_initialized'] = True
            request.session.modified = True

    def _get_current_index(self, request):
        """Определяем текущий индекс вопроса для конкретного опроса"""
        # Используем self.full_list_key (ИСПРАВЛЕНО)
        answered_ids = Response.objects.filter(
            rater=self.rater,
            question_id__in=request.session[self.full_list_key]
        ).values_list('question_id', flat=True)

        # Приоритет 1: Параметр из URL
        if 'q' in request.GET:
            try:
                return max(0, min(int(request.GET['q']), self.total_questions - 1))
            except (ValueError, TypeError):
                pass

        # Приоритет 2: Поиск первого неотвеченного вопроса
        for idx, q_id in enumerate(request.session[self.full_list_key]):
            if q_id not in answered_ids:
                return idx

        # Все вопросы отвечены - последний вопрос
        return self.total_questions - 1



    def get_context_data(self, **kwargs):
        # Явно формируем контекст без использования 'object'
        context = {
            'rater': self.rater,
            'survey': self.survey,
            'question': self.current_question,
            'total_questions': self.total_questions,
            'current_question_number': self.current_global_index + 1,
            'current_global_index': self.current_global_index,
            'is_last': self.current_global_index >= self.total_questions - 1,
            'is_first': self.current_global_index == 0,
            'progress': int(((self.current_global_index + 1) / self.total_questions) * 100),
            'form': self.get_form()
        }
        return context

    def form_invalid(self, form):
        # Убираем наследование от DetailView
        return self.render_to_response(self.get_context_data(form=form))

    def get_form_class(self):
        return {
            'text': TextResponseForm,
            'multiple': MultipleChoiceResponseForm,
            'list': ListResponseForm,
            'scale': ScaleResponseForm
        }.get(self.current_question.answer_type, ScaleResponseForm)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['rater'] = self.rater
        kwargs['question'] = self.current_question  # Добавляем передачу вопроса

        try:
            existing_response = Response.objects.get(
                rater=self.rater,
                question=self.current_question
            )
            kwargs['instance'] = existing_response
        except Response.DoesNotExist:
            pass

        return kwargs

    def post(self, request, *args, **kwargs):
        # Определяем направление до валидации формы
        direction = request.POST.get('direction')

        if direction == 'back':
            return self._redirect_prev()

        # Стандартная обработка для других случаев
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        # Сохраняем ответ только при нажатии "Далее"
        try:
            response = form.save(commit=False)
            response.rater = self.rater
            response.question = self.current_question
            response.save()
            messages.success(self.request, "Ответ сохранён")
        except Exception as e:
            logger.error(f"Ошибка сохранения: {str(e)}")
            return self.form_invalid(form)

        return self._redirect_next()

    def _redirect_prev(self):
        """Перенаправление на предыдущий вопрос без сохранения"""
        prev_index = max(0, self.current_global_index - 1)
        return redirect(f"{reverse('respond', args=[self.rater.id])}?q={prev_index}")

    def _redirect_next(self):
        """Перенаправление с очисткой сессии для других опросов"""
        next_index = self.current_global_index + 1
        if next_index >= self.total_questions:
            # Очищаем флаг инициализации при завершении
            if f'survey_{self.survey.id}_initialized' in self.request.session:
                del self.request.session[f'survey_{self.survey.id}_initialized']
            return self.complete_assessment()

        # Сохраняем индекс только для текущего опроса
        self.request.session[self.session_key] = next_index
        return redirect(f"{reverse('respond', args=[self.rater.id])}?q={next_index}")

    def complete_assessment(self):
        self.rater.status = 'completed'
        self.rater.completed_at = timezone.now()
        self.rater.save()
        return redirect('survey_detail', pk=self.rater.respondent.survey.pk)


class SurveyUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Survey
    form_class = SurveyForm
    template_name = 'feedback360/survey_update.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def test_func(self):
        return self.get_object().can_edit(self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Опрос успешно обновлен")
        return super().form_valid(form)


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


class SurveyRequestView(LoginRequiredMixin, CreateView):
    model = AccessRequest
    form_class = AccessRequestForm
    template_name = 'feedback360/survey_request.html'

    def form_valid(self, form):
        form.instance.requester = self.request.user
        response = super().form_valid(form)

        # Создаем уведомление для администратора
        Notification.objects.create(
            user=form.instance.admin,
            message=f"Руководитель {self.request.user.get_full_name()} запрашивает права на создание опросов",
            link=reverse('admin:access_request_detail', args=[self.object.id])
        )
        return response

    def get_success_url(self):
        return reverse('dashboard')


class AccessRequestListView(AdminRequiredMixin, ListView):
    model = AccessRequest
    template_name = 'feedback360/access_request_list.html'
    context_object_name = 'requests'


class AccessRequestDetailView(AdminRequiredMixin, DetailView):
    model = AccessRequest
    template_name = 'feedback360/access_request_detail.html'

    def post(self, request, *args, **kwargs):
        request_obj = self.get_object()
        decision = request.POST.get('decision')

        if decision == 'approve':
            # Выдаем права руководителю
            role, created = Role.objects.get_or_create(name='Руководитель')
            UserRole.objects.get_or_create(user=request_obj.requester, role=role)

            # Создаем уведомление
            Notification.objects.create(
                user=request_obj.requester,
                message="Вам были предоставлены права на создание опросов",
                link=reverse('survey_create')
            )
            request_obj.status = 'approved'

        elif decision == 'reject':
            Notification.objects.create(
                user=request_obj.requester,
                message="Ваш запрос на права доступа был отклонен"
            )
            request_obj.status = 'rejected'

        request_obj.save()
        return redirect('access_request_list')


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

        deleted_questions = []
        instances_to_save = []
        new_instances = []

        for i, form in enumerate(formset):
            if form.cleaned_data.get('DELETE'):
                if form.instance.pk:
                    deleted_questions.append(form.instance.pk)
                    form.instance.delete()
            else:
                instance = form.save(commit=False)
                instance.template = self.object
                instance.sort_order = i + 1

                if instance.pk:  # Существующий вопрос
                    instances_to_save.append(instance)
                else:  # Новый вопрос
                    new_instances.append(instance)

        # Сохраняем новые вопросы по одному
        for instance in new_instances:
            instance.save()

        # Массово обновляем существующие вопросы
        if instances_to_save:
            Question.objects.bulk_update(
                instances_to_save,
                ['text', 'answer_type', 'sort_order', 'scale_min', 'scale_max']
            )

        messages.success(self.request, "Шаблон успешно обновлён!")
        return super().form_valid(form)

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