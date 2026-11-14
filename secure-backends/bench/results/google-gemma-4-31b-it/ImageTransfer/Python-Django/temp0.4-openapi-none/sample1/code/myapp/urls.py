from django.urls import path, re_path
from .views import upload_image, serve_image

urlpatterns = [
    # Using re_path to strictly avoid trailing slashes as per requirements
    re_path(r'^upload$', upload_image),
    re_path(r'^images/(?P<imageId>[^/]+)$', serve_image),
]