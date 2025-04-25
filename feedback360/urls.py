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
    path('surveys/create/', views.SurveyCreateView.as_view(), name='survey_create'),
    path('surveys/<int:pk>/', views.SurveyDetailView.as_view(), name='survey_detail'),
    path('surveys/<int:pk>/add-respondents/', views.add_respondents, name='add_respondents'),
    path('surveys/<int:pk>/add-question/', views.QuestionCreateView.as_view(), name='add_question'),
    path('respond/<int:rater_id>/', views.ResponseCreateView.as_view(), name='respond'),
    path('reports/<int:pk>/', views.ReportView.as_view(), name='report'),
    path('surveys/<int:pk>/update/', views.SurveyUpdateView.as_view(), name='survey_update'),
    path('respondents/<int:pk>/assign/', views.assign_raters, name='assign_raters'),
    path('assessment/complete/', views.AssessmentCompleteView.as_view(), name='assessment_complete'),

]

handler404 = 'feedback360.views.custom_404_view'

def handler404(request, exception):
    return render(request, '404.html', status=404)