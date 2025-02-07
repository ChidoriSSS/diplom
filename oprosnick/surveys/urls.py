from django.urls import path
from . import views

urlpatterns = [
    path('', views.survey_list, name='survey_list'),
    path('<int:survey_id>/', views.survey_detail, name='survey_detail'),
    path('questions/<int:question_id>/', views.question_detail, name='question_detail'),
]