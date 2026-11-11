from django.urls import path
from .views import SearchFilesView

urlpatterns = [
    # No trailing slash as requested
    path('search', SearchFilesView.as_view(), name='search'),
]