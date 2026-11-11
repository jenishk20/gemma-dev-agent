from django.urls import path
from .views import heartbeat, services_overview

urlpatterns = [
    path('heartbeat', heartbeat, name='heartbeat'),
    path('services', services_overview, name='services_overview'),
]