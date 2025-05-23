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
    path('surveys/<int:pk>/add-question/', views.QuestionCreateView.as_view(), name='add_question'),
    path('leader/survey/create/', views.LeaderSurveyCreateView.as_view(), name='leader_survey_create'),
    path('leader/survey/<int:pk>/edit/', views.LeaderSurveyUpdateView.as_view(), name='leader_survey_edit'),
    path('surveys/get-template-questions/<int:template_id>/', views.get_template_questions, name='get_template_questions'),
    path('templates/', views.TemplateListView.as_view(), name='template_list'),
    path('templates/<int:pk>/edit/', views.TemplateUpdateView.as_view(), name='template_edit'),
    path('template/<int:pk>/delete/', views.TemplateDeleteView.as_view(), name='template_delete'),
    path('templates/<int:template_pk>/questions/<int:question_pk>/delete/', views.QuestionDeleteView.as_view(), name='template_question_delete'),
    path('surveys/get-template-questions/<int:template_id>/', views.get_template_questions, name='get_template_questions'),

]

handler404 = 'feedback360.views.custom_404_view'

def handler404(request, exception):
    return render(request, '404.html', status=404)

