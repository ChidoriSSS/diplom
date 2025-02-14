from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from .models import Survey, Question, Option, Response, SurveyParticipant

# Опросы
class SurveyListView(ListView):
    model = Survey
    template_name = 'surveys/survey_list.html'
    context_object_name = 'surveys'

class SurveyDetailView(DetailView):
    model = Survey
    template_name = 'surveys/survey_detail.html'
    context_object_name = 'survey'

class SurveyCreateView(CreateView):
    model = Survey
    template_name = 'surveys/survey_form.html'
    fields = ['title', 'description', 'created_by']
    success_url = reverse_lazy('survey_list')

class SurveyUpdateView(UpdateView):
    model = Survey
    template_name = 'surveys/survey_form.html'
    fields = ['title', 'description']
    success_url = reverse_lazy('survey_list')

class SurveyDeleteView(DeleteView):
    model = Survey
    template_name = 'surveys/survey_confirm_delete.html'
    success_url = reverse_lazy('survey_list')

# Вопросы
class QuestionListView(ListView):
    model = Question
    template_name = 'surveys/question_list.html'
    context_object_name = 'questions'

    def get_queryset(self):
        return Question.objects.filter(survey_id=self.kwargs['survey_id'])

class QuestionCreateView(CreateView):
    model = Question
    template_name = 'surveys/question_form.html'
    fields = ['survey', 'question_text', 'question_type']
    success_url = reverse_lazy('survey_list')

class QuestionUpdateView(UpdateView):
    model = Question
    template_name = 'surveys/question_form.html'
    fields = ['question_text', 'question_type']
    success_url = reverse_lazy('survey_list')

class QuestionDeleteView(DeleteView):
    model = Question
    template_name = 'surveys/question_confirm_delete.html'
    success_url = reverse_lazy('survey_list')

# Варианты ответов
class OptionListView(ListView):
    model = Option
    template_name = 'surveys/option_list.html'
    context_object_name = 'options'

    def get_queryset(self):
        return Option.objects.filter(question_id=self.kwargs['question_id'])

class OptionCreateView(CreateView):
    model = Option
    template_name = 'surveys/option_form.html'
    fields = ['question', 'option_text']
    success_url = reverse_lazy('survey_list')

class OptionUpdateView(UpdateView):
    model = Option
    template_name = 'surveys/option_form.html'
    fields = ['option_text']
    success_url = reverse_lazy('survey_list')

class OptionDeleteView(DeleteView):
    model = Option
    template_name = 'surveys/option_confirm_delete.html'
    success_url = reverse_lazy('survey_list')

# Ответы
class ResponseListView(ListView):
    model = Response
    template_name = 'surveys/response_list.html'
    context_object_name = 'responses'

    def get_queryset(self):
        return Response.objects.filter(question_id=self.kwargs['question_id'])

class ResponseCreateView(CreateView):
    model = Response
    template_name = 'surveys/response_form.html'
    fields = ['question', 'user', 'answer_text']
    success_url = reverse_lazy('survey_list')

class ResponseUpdateView(UpdateView):
    model = Response
    template_name = 'surveys/response_form.html'
    fields = ['answer_text']
    success_url = reverse_lazy('survey_list')

class ResponseDeleteView(DeleteView):
    model = Response
    template_name = 'surveys/response_confirm_delete.html'
    success_url = reverse_lazy('survey_list')

# Участники опросов
class SurveyParticipantListView(ListView):
    model = SurveyParticipant
    template_name = 'surveys/survey_participant_list.html'
    context_object_name = 'participants'

    def get_queryset(self):
        return SurveyParticipant.objects.filter(survey_id=self.kwargs['survey_id'])

class SurveyParticipantCreateView(CreateView):
    model = SurveyParticipant
    template_name = 'surveys/survey_participant_form.html'
    fields = ['survey', 'user', 'status']
    success_url = reverse_lazy('survey_list')

class SurveyParticipantUpdateView(UpdateView):
    model = SurveyParticipant
    template_name = 'surveys/survey_participant_form.html'
    fields = ['status']
    success_url = reverse_lazy('survey_list')

class SurveyParticipantDeleteView(DeleteView):
    model = SurveyParticipant
    template_name = 'surveys/survey_participant_confirm_delete.html'
    success_url = reverse_lazy('survey_list')