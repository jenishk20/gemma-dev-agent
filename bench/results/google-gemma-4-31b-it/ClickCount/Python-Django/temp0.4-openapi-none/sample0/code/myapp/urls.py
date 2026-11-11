from django.urls import path
from .views import ClickView, ClicksListView

urlpatterns = [
    path('click', ClickView.as_view(), name='register_click'),
    path('clicks', ClicksListView.as_view(), name='retrieve_clicks'),
]