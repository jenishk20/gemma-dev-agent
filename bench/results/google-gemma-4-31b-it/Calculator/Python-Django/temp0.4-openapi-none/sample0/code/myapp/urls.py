from django.urls import path
from .views import calculator_view

urlpatterns = [
    # No trailing slash as per requirement
    path('calculator', calculator_view, name='calculator'),
]