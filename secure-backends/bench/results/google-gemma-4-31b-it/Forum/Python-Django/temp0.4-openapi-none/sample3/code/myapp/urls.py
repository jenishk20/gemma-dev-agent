from django.urls import path
from .views import messages_view

urlpatterns = [
    # Using a lambda or a custom regex to ensure no trailing slash is required/added
    path('messages', messages_view),
]