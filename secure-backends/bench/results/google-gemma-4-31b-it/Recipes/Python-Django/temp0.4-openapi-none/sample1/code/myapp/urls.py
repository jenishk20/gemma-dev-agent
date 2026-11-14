from django.urls import path
from . import views

urlpatterns = [
    path('recipes', views.recipe_overview, name='recipe_overview'),
    path('recipes/upload', views.upload_recipe, name='upload_recipe'),
    path('recipes/<int:recipeId>', views.get_recipe_detail, name='recipe_detail'),
    path('recipes/<int:recipeId>/comments', views.add_comment, name='add_comment'),
    path('recipes/<int:recipeId>/ratings', views.add_rating, name='add_rating'),
]