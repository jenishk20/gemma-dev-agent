from django.urls import path
from .views import click_view, clicks_view

urlpatterns = [
    path('click', click_view),
    path('clicks', clicks_view),
]