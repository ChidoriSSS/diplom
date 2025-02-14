# oprosnick/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('surveys/', include('surveys.urls')),  # Подключите urls.py из приложения surveys
]
