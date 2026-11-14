from django.urls import path
from .views import create_gif_view

urlpatterns = [
    path('create-gif', create_gif_view, name='create_gif'),
]