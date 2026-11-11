from django.urls import path
from .views import invite_user, create_user

urlpatterns = [
    path('invite_user', invite_user),
    path('create_user', create_user),
]