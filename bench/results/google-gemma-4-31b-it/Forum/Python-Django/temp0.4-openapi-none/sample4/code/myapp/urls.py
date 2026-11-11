from django.urls import path
from .views import messages_view

urlpatterns = [
    # Use a lambda or custom path to avoid trailing slash as per requirement
    path('messages', messages_view, name='messages'),
]