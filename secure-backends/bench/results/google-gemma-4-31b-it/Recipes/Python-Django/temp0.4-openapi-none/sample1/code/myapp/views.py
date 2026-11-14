import json
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from .models import Recipe, Comment, Rating
from django.db.models import Avg

@csrf_exempt
def recipe_overview(request):
    if request.method == 'GET':
        recipes = Recipe.objects.all().order_by('-id')
        html = "<h1>Recipe Overview</h1><ul>"
        for r in recipes:
            html += f'<li><a href="/recipes/{r.id}">{r.title}</a></li>'
        html += "</ul>"
        return HttpResponse(html)
    return HttpResponse(status=405)

@csrf_exempt
def upload_recipe(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            recipe = Recipe.objects.create(
                title=data['title'],
                ingredients=data['ingredients'],
                instructions=data['instructions']
            )
            return JsonResponse({
                "id": str(recipe.id),
                "title": recipe.title,
                "ingredients": recipe.ingredients,
                "instructions": recipe.instructions,
                "comments": [],
                "avgRating": None
            }, status=201)
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({"error": "Invalid input"}, status=400)
    return HttpResponse(status=405)

def get_recipe_detail(request, recipeId):
    recipe = get_object_or_404(Recipe, pk=recipeId)
    avg_rating = recipe.get_avg_rating()
    
    # The schema asks for text/html for this endpoint
    html = f"<h1>{recipe.title}</h1>"
    html += f"<h3>Ingredients</h3><ul>"
    for ing in recipe.ingredients:
        html += f"<li>{ing}</li>"
    html += "</ul>"
    html += f"<h3>Instructions</h3><p>{recipe.instructions}</p>"
    html += f"<h3>Average Rating: {avg_rating if avg_rating else 'N/A'}</h3>"
    html += "<h3>Comments</h3><ul>"
    for c in recipe.comments.all():
        html += f"<li>{c.comment}</li>"
    html += "</ul>"
    
    return HttpResponse(html)

@csrf_exempt
def add_comment(request, recipeId):
    if request.method == 'POST':
        recipe = get_object_or_404(Recipe, pk=recipeId)
        try:
            data = json.loads(request.body)
            Comment.objects.create(recipe=recipe, comment=data['comment'])
            return HttpResponse(status=201)
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({"error": "Invalid input"}, status=400)
    return HttpResponse(status=405)

@csrf_exempt
def add_rating(request, recipeId):
    if request.method == 'POST':
        recipe = get_object_or_404(Recipe, pk=recipeId)
        try:
            data = json.loads(request.body)
            rating_val = data['rating']
            if not (1 <= rating_val <= 5):
                return JsonResponse({"error": "Rating must be between 1 and 5"}, status=400)
            Rating.objects.create(recipe=recipe, rating=rating_val)
            return HttpResponse(status=201)
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({"error": "Invalid input"}, status=400)
    return HttpResponse(status=405)