from django.urls import path
from .views import click_handler, clicks_handler

urlpatterns = [
    path('click', click_handler, name='register_click'),
    path('clicks', clicks_handler, name='retrieve_clicks'),
]