from django.urls import path
from . import views

urlpatterns = [
    path('add', views.add_product, name='add'),
    path('download', views.download_product, name='download'),
    path('upload', views.upload_product, name='upload'),
    path('search', views.search_products, name='search'),
]