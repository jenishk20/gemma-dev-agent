from django.urls import path
from .views import recipe_list_or_create, recipe_detail, add_comment, add_rating

urlpatterns = [
    path('recipes', recipe_list_or_create),
    path('recipes/upload', recipe_list_or_create), # Re-using the same view for POST /recipes/upload
    path('recipes/<int:recipeId>', recipe_detail),
    path('recipes/<int:recipeId>/comments', add_comment),
    path('recipes/<int:recipeId>/ratings', add_rating),
]