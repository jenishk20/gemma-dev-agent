from django.urls import path
from . import views

urlpatterns = [
    path('entries', views.entries_view),
    path('entries/<int:entryId>', views.entry_detail_view),
    path('entries/<int:entryId>/edits', views.entry_edits_view),
]