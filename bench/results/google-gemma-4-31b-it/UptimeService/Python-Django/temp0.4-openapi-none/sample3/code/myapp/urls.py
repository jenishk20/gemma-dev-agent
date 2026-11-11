from django.urls import path
from . import views

urlpatterns = [
    # Using regex or specific paths to avoid trailing slash as per requirement
    path('heartbeat', views.heartbeat),
    path('services', views.services_overview),
]