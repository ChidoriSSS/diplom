from django.shortcuts import render
from django.urls import path
from . import views
from django.contrib.auth.views import LoginView, LogoutView


urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', views.profile, name='profile'),
    path('surveys/', views.SurveyListView.as_view(), name='survey_list'),
    path('template/create/', views.TemplateCreateView.as_view(), name='template_create'),
    path('surveys/create/', views.SurveyCreateView.as_view(), name='survey_create'),
    path('surveys/<int:pk>/', views.SurveyDetailView.as_view(), name='survey_detail'),
    path('surveys/<int:pk>/add-respondents/', views.add_respondents, name='add_respondents'),
    path('surveys/<int:pk>/add-question/', views.QuestionCreateView.as_view(), name='add_question'),
    path('respond/<int:rater_id>/', views.ResponseCreateView.as_view(), name='respond'),
    path('reports/<int:pk>/', views.ReportView.as_view(), name='report'),
    path('surveys/<int:pk>/update/', views.SurveyUpdateView.as_view(), name='survey_update'),
    path('respondents/<int:pk>/assign/', views.assign_raters, name='assign_raters'),
    path('assessment/complete/', views.AssessmentCompleteView.as_view(), name='assessment_complete'),
    path('leader/survey/create/', views.LeaderSurveyCreateView.as_view(), name='leader_survey_create'),
    path('leader/survey/<int:pk>/edit/', views.LeaderSurveyUpdateView.as_view(), name='leader_survey_edit'),
    path('surveys/<int:pk>/edit-questions/', views.SurveyQuestionsEditView.as_view(), name='edit_survey_questions'),
    path('surveys/get-template-questions/<int:template_id>/', views.get_template_questions, name='get_template_questions'),
    path('request-survey/', views.SurveyRequestView.as_view(), name='survey_request'),
    path('admin/access-requests/', views.AccessRequestListView.as_view(), name='access_request_list'),
    path('admin/access-requests/<int:pk>/', views.AccessRequestDetailView.as_view(), name='access_request_detail'),
    path('templates/', views.TemplateListView.as_view(), name='template_list'),
    path('templates/<int:pk>/edit/', views.TemplateUpdateView.as_view(), name='template_edit'),
    path('template/<int:pk>/delete/', views.TemplateDeleteView.as_view(), name='template_delete'),
    path('templates/<int:template_pk>/questions/<int:question_pk>/delete/', views.QuestionDeleteView.as_view(), name='template_question_delete'),
    path('surveys/get-template-questions/<int:template_id>/', views.get_template_questions, name='get_template_questions'),

]

handler404 = 'feedback360.views.custom_404_view'

def handler404(request, exception):
    return render(request, '404.html', status=404)

