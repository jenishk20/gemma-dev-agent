from django.urls import path
from .views import click_register, click_retrieve

urlpatterns = [
    path('click', click_register, name='click_register'),
    path('clicks', click_retrieve, name='click_retrieve'),
]