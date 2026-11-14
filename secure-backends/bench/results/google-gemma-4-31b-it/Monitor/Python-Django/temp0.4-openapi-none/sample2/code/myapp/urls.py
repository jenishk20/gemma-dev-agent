from django.urls import path
from .views import monitor_commands

urlpatterns = [
    path('monitor/commands', monitor_commands, name='monitor_commands'),
]