from django.urls import path
from .views import handle_click, retrieve_clicks

urlpatterns = [
    path('click', handle_click, name='register_click'),
    path('clicks', retrieve_clicks, name='retrieve_clicks'),
]