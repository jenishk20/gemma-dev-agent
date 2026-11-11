from django.urls import path
from . import views

urlpatterns = [
    path('recipes', views.recipe_overview, name='overview'),
    path('recipes/upload', views.upload_recipe, name='upload'),
    path('recipes/<int:recipeId>', views.recipe_detail, name='detail'),
    path('recipes/<int:recipeId>/comments', views.add_comment, name='comment'),
    path('recipes/<int:recipeId>/ratings', views.add_rating, name='rating'),
]