from django.urls import path, re_path
from .views import upload_image, serve_image

urlpatterns = [
    path('upload', upload_image, name='upload'),
    re_path(r'images/(?P<imageId>[^/]+)$', serve_image, name='serve_image'),
]