from django.urls import path
from . import views

urlpatterns = [
    path('entries', views.entries_list_create, name='entries_list_create'),
    path('entries/<str:entryId>', views.entry_detail_update, name='entry_detail_update'),
    path('entries/<str:entryId>/edits', views.entry_history, name='entry_history'),
]