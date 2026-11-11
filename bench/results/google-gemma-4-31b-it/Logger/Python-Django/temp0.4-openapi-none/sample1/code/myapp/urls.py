from django.urls import path
from .views import log_message, retrieve_logs

urlpatterns = [
    path('log', log_message, name='log_message'),
    path('logs', retrieve_logs, name='retrieve_logs'),
]