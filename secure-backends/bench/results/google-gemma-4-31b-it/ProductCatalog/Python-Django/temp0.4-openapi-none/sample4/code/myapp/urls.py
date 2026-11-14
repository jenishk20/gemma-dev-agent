from django.urls import re_path
from .views import api_router

urlpatterns = [
    # Match /add, /download, /upload, /search exactly
    re_path(r'^(add|download|upload|search)$', api_router),
]