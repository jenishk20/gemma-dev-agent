import json
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from .models import Recipe, Comment, Rating

def recipe_overview(request):
    recipes = Recipe.objects.all()
    html = "<h1>Recipe Overview</h1><ul>"
    for r in recipes:
        html += f"<li><a href='/recipes/{r.id}'>{r.title}</a></li>"
    html += "</ul>"
    return HttpResponse(html)

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
                "id": recipe.id,
                "title": recipe.title,
                "ingredients": recipe.ingredients,
                "instructions": recipe.instructions,
                "comments": [],
                "avgRating": None
            }, status=201)
        except (KeyError, json.JSONDecodeError):
            return HttpResponse("Invalid input", status=400)
    return HttpResponse("Method not allowed", status=405)

def recipe_detail(request, recipeId):
    recipe = get_object_or_404(Recipe, pk=recipeId)
    avg = recipe.get_avg_rating()
    comments = Comment.objects.filter(recipe=recipe)
    
    html = f"<h1>{recipe.title}</h1>"
    html += f"<h3>Ingredients</h3><ul>"
    for ing in recipe.ingredients:
        html += f"<li>{ing}</li>"
    html += "</ul>"
    html += f"<h3>Instructions</h3><p>{recipe.instructions}</p>"
    html += f"<h3>Average Rating: {avg if avg else 'No ratings yet'}</h3>"
    html += "<h3>Comments</h3><ul>"
    for c in comments:
        html += f"<li>{c.text}</li>"
    html += "</ul>"
    return HttpResponse(html)

@csrf_exempt
def add_comment(request, recipeId):
    if request.method == 'POST':
        recipe = get_object_or_404(Recipe, pk=recipeId)
        try:
            data = json.loads(request.body)
            Comment.objects.create(recipe=recipe, text=data['comment'])
            return HttpResponse("Comment added successfully", status=201)
        except (KeyError, json.JSONDecodeError):
            return HttpResponse("Invalid input", status=400)
    return HttpResponse("Method not allowed", status=405)

@csrf_exempt
def add_rating(request, recipeId):
    if request.method == 'POST':
        recipe = get_object_or_404(Recipe, pk=recipeId)
        try:
            data = json.loads(request.body)
            val = data['rating']
            if not (1 <= val <= 5):
                return HttpResponse("Rating must be between 1 and 5", status=400)
            Rating.objects.create(recipe=recipe, value=val)
            return HttpResponse("Rating added successfully", status=201)
        except (KeyError, json.JSONDecodeError):
            return HttpResponse("Invalid input", status=400)
    return HttpResponse("Method not allowed", status=405)