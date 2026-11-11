from django.urls import path
from .views import register_merchant, login_merchant, upload_wares, list_wares

urlpatterns = [
    path('merchants/register', register_merchant, name='register'),
    path('merchants/login', login_merchant, name='login'),
    path('merchants/upload-wares', upload_wares, name='upload'),
    path('wares', list_wares, name='wares'),
]