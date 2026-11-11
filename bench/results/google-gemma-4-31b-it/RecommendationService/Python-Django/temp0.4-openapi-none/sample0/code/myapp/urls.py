from django.urls import path
from .views import recommender

urlpatterns = [
    # No trailing slash as per requirement
    path('recommender', recommender),
]