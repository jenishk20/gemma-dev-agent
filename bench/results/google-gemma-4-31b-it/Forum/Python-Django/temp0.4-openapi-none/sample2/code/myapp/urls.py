from django.urls import path
from .views import messages_view

urlpatterns = [
    # Removing trailing slash as requested by the prompt
    path('messages', messages_view, name='messages'),
]