from django.urls import path
from .views import log_handler

urlpatterns = [
    path('log', log_handler, name='log'),
    path('logs', log_handler, name='logs'),
]