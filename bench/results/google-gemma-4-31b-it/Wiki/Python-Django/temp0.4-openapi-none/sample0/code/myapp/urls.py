from django.urls import path
from .views import entries_view, edits_view, update_helper

urlpatterns = [
    path('entries', entries_view, name='entries_list'),
    path('entries/<str:entryId>', entries_view, name='entry_detail'),
    path('entries/<str:entryId>/edits', edits_view, name='entry_edits'),
    path('update/<str:entryId>', update_helper, name='update_helper'),
]