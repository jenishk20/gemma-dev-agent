from django.urls import path, re_path
from .views import UploadImageView, ServeImageView

urlpatterns = [
    # Using re_path or specific path to avoid trailing slash requirements of Django's default path
    path('upload', UploadImageView.as_view(), name='upload'),
    path('images/<uuid:imageId>', ServeImageView.as_view(), name='serve_image'),
]