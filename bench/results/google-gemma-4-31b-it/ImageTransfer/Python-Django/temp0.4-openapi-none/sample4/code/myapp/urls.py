from django.urls import path, re_path
from .views import upload_image, serve_image

urlpatterns = [
    path('upload', upload_image),
    # Using re_path or path with converters to handle the imageId without trailing slash
    path('images/<uuid:imageId>', serve_image),
]