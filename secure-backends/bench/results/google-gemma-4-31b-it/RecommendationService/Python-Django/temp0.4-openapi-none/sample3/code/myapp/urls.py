from django.urls import path
from .views import recommender

urlpatterns = [
    # Note: The requirement specifies no trailing slashes
    path('recommender', recommender),
]