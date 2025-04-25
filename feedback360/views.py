from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.db.models import Q
from django.http import Http404
from django.views.generic import (
    ListView, DetailView, CreateView,
    UpdateView, TemplateView
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.utils import timezone
from .models import Survey, Respondent, Question, Response, Report, User, Rater, Competency, SurveyTemplate
from .forms import SurveyForm, RespondentForm, QuestionForm, ResponseForm, RaterAssignmentForm, TextResponseForm, \
    MultipleChoiceResponseForm, ScaleResponseForm, ListResponseForm
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.decorators import login_required
import logging
logger = logging.getLogger(__name__)


@login_required
def profile(request):
    return render(request, 'feedback360/profile.html', {
        'user': request.user
    })

class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return user_has_admin_access(self.request.user)

def user_has_admin_access(user):
    return user.is_superuser or user.userrole_set.filter(role__name='Администратор').exists()

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'feedback360/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        user = self.request.user

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
            survey.categories = survey.template.competencies.values_list(
                'category',
                flat=True
            ).distinct()

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
            'categories': Competency.objects.values_list('category', flat=True).distinct(),
            'selected_category': category,
            'sort_mode': sort_by
        })
        return context


class SurveyCreateView(AdminRequiredMixin, CreateView):
    model = Survey
    form_class = SurveyForm
    template_name = 'feedback360/survey_create.html'
    success_url = reverse_lazy('survey_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(
            self.request,
            "Пожалуйста, исправьте ошибки в форме",
            extra_tags='alert-danger'
        )
        return super().form_invalid(form)

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
        return redirect('assessment_complete')

class AssessmentCompleteView(LoginRequiredMixin, TemplateView):
    template_name = 'feedback360/assessment_complete.html'

def assign_raters(request, pk):
    respondent = get_object_or_404(Respondent, pk=pk)
    survey = respondent.survey

    if not user_has_admin_access(request.user):
        messages.error(request, "У вас нет прав для назначения оценивающих")
        return redirect('survey_detail', pk=survey.id)

    available_users = User.objects.exclude(
        id=respondent.user.id
    ).exclude(
        id__in=respondent.raters.values_list('user_id', flat=True)
    )

    form = RaterAssignmentForm(
        available_users=available_users,
        data=request.POST or None
    )

    if request.method == 'POST' and form.is_valid():
        for user in form.cleaned_data['raters']:
            Rater.objects.create(
                respondent=respondent,
                user=user,
                relationship_type=form.cleaned_data['relationship_type']
            )
        messages.success(request, "Оценивающие успешно назначены")
        return redirect('survey_detail', pk=survey.id)

    return render(request, 'feedback360/assign_raters.html', {
        'respondent': respondent,
        'survey': survey,
        'form': form,
        'available_users': available_users
    })


class ReportView(LoginRequiredMixin, DetailView):
    model = Report
    template_name = 'feedback360/report.html'
    context_object_name = 'report'

    def get_object(self, queryset=None):
        report = super().get_object(queryset)
        if report.respondent.user != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied
        return report

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['questions'] = Question.objects.filter(
                competency__template=self.object.survey.template
            )
        except Survey.DoesNotExist:
            context['questions'] = []
        return context

@receiver(post_save, sender=Respondent)
def create_report(sender, instance, created, **kwargs):
    if created:
        Report.objects.create(
            respondent=instance,
            survey=instance.survey,
            report_data={'summary': {}, 'details': []}
        )


class SurveyUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Survey
    form_class = SurveyForm
    template_name = 'feedback360/survey_update.html'

    def get_success_url(self):
        return reverse_lazy('survey_detail', kwargs={'pk': self.object.id})

    def form_valid(self, form):
        messages.success(self.request, "Опрос успешно обновлен")
        return super().form_valid(form)

    def test_func(self):
        survey = self.get_object()
        return user_has_admin_access(self.request.user) or survey.created_by == self.request.user


def add_respondents(request, pk):
    survey = get_object_or_404(Survey, pk=pk)

    if not user_has_admin_access(request.user):
        messages.error(request, "У вас нет прав для добавления участников")
        return redirect('survey_detail', pk=survey.id)

    if request.method == 'POST':
        user_ids = request.POST.getlist('users', [])
        if not user_ids:
            messages.warning(request, "Выберите хотя бы одного участника")
            return redirect('survey_detail', pk=pk)

        users = User.objects.filter(id__in=user_ids)
        existing_users = survey.respondents.values_list('user_id', flat=True)

        # Создаем только новых участников
        new_users = users.exclude(id__in=existing_users)
        created_count = 0

        for user in new_users:
            Respondent.objects.create(survey=survey, user=user)
            created_count += 1

        if created_count > 0:
            messages.success(request, f"Добавлено {created_count} новых участников")
        else:
            messages.info(request, "Все выбранные пользователи уже являются участниками")

        return redirect('survey_detail', pk=survey.id)

        # Для GET запроса показываем форму
    available_users = User.objects.exclude(
        id__in=survey.respondents.values_list('user_id', flat=True)
    )
    return render(request, 'feedback360/add_respondents.html', {
        'survey': survey,
        'available_users': available_users
    })

def custom_404_view(request, exception):
    return render(request, 'feedback360/404.html', status=404)

