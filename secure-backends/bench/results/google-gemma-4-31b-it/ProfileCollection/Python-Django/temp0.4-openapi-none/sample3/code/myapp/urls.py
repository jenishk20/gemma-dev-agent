from django.urls import path
from .views import add_profile, get_profile, get_profile_photo

urlpatterns = [
    path('add_profile', add_profile),
    path('profile/<str:username>', get_profile),
    path('profile-photo/<str:username>', get_profile_photo),
]