from django.urls import path
from . import views

urlpatterns = [
    # Опросы
    path('', views.SurveyListView.as_view(), name='survey_list'),
    path('<int:pk>/', views.SurveyDetailView.as_view(), name='survey_detail'),
    path('create/', views.SurveyCreateView.as_view(), name='survey_create'),
    path('<int:pk>/update/', views.SurveyUpdateView.as_view(), name='survey_update'),
    path('<int:pk>/delete/', views.SurveyDeleteView.as_view(), name='survey_delete'),

    # Вопросы
    path('<int:survey_id>/questions/', views.QuestionListView.as_view(), name='question_list'),
    path('<int:survey_id>/questions/create/', views.QuestionCreateView.as_view(), name='question_create'),
    path('questions/<int:pk>/update/', views.QuestionUpdateView.as_view(), name='question_update'),
    path('questions/<int:pk>/delete/', views.QuestionDeleteView.as_view(), name='question_delete'),

    # Варианты ответов
    path('questions/<int:question_id>/options/', views.OptionListView.as_view(), name='option_list'),
    path('questions/<int:question_id>/options/create/', views.OptionCreateView.as_view(), name='option_create'),
    path('options/<int:pk>/update/', views.OptionUpdateView.as_view(), name='option_update'),
    path('options/<int:pk>/delete/', views.OptionDeleteView.as_view(), name='option_delete'),

    # Ответы
    path('questions/<int:question_id>/responses/', views.ResponseListView.as_view(), name='response_list'),
    path('questions/<int:question_id>/responses/create/', views.ResponseCreateView.as_view(), name='response_create'),
    path('responses/<int:pk>/update/', views.ResponseUpdateView.as_view(), name='response_update'),
    path('responses/<int:pk>/delete/', views.ResponseDeleteView.as_view(), name='response_delete'),

    # Участники опросов
    path('<int:survey_id>/participants/', views.SurveyParticipantListView.as_view(), name='survey_participant_list'),
    path('<int:survey_id>/participants/add/', views.SurveyParticipantCreateView.as_view(), name='survey_participant_add'),
    path('participants/<int:pk>/update/', views.SurveyParticipantUpdateView.as_view(), name='survey_participant_update'),
    path('participants/<int:pk>/delete/', views.SurveyParticipantDeleteView.as_view(), name='survey_participant_delete'),
]