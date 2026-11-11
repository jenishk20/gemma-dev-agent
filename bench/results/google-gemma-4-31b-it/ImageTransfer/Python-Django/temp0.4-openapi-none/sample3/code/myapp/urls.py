from django.urls import path
from .views import UploadImageView, ServeImageView

urlpatterns = [
    path('upload', UploadImageView.as_view(), name='upload'),
    path('images/<uuid:imageId>', ServeImageView.as_view(), name='serve_image'),
]