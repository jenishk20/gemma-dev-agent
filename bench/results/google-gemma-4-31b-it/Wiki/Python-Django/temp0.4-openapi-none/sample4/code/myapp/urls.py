from django.urls import path
from .views import entries_view, entry_detail_view, entry_edits_view

urlpatterns = [
    path('entries', entries_view, name='entries'),
    path('entries/<str:entryId>', entry_detail_view, name='entry_detail'),
    path('entries/<str:entryId>/edits', entry_edits_view, name='entry_edits'),
]