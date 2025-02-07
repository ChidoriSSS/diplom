from django.contrib import admin
from django.urls import path, include

from surveys import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('surveys/', views.survey_list, name='survey_list'),
    path('surveys/<int:survey_id>/', views.survey_detail, name='survey_detail'),
    path('questions/<int:question_id>/', views.question_detail, name='question_detail'),
]
