import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from .models import Recipe, Comment, Rating

@csrf_exempt
def recipes_view(request, recipe_id=None):
    # GET /recipes
    if recipe_id is None and request.method == 'GET':
        recipes = Recipe.objects.all()
        html = "<html><body><h1>Recipes</h1><ul>"
        for r in recipes:
            html += f'<li><a href="/recipes/{r.id}">{r.title}</a></li>'
        html += "</ul></body></html>"
        return HttpResponse(html)

    # GET /recipes/{recipeId}
    if recipe_id is not None and request.method == 'GET':
        recipe = get_object_or_404(Recipe, pk=recipe_id)
        avg = recipe.get_avg_rating()
        comments = Comment.objects.filter(recipe=recipe)
        
        html = f"<html><body><h1>{recipe.title}</h1>"
        html += f"<p><b>Ingredients:</b> {', '.join(recipe.ingredients)}</p>"
        html += f"<p><b>Instructions:</b> {recipe.instructions}</p>"
        html += f"<p><b>Average Rating:</b> {avg}</p>"
        html += "<h3>Comments</h3><ul>"
        for c in comments:
            html += f"<li>{c.text}</li>"
        html += "</ul></body></html>"
        return HttpResponse(html)

    return HttpResponse("Not Found", status=404)

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
                "avgRating": recipe.get_avg_rating()
            }, status=201)
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({"error": "Invalid input"}, status=400)
    return HttpResponse("Method Not Allowed", status=405)

@csrf_exempt
def add_comment(request, recipe_id):
    if request.method == 'POST':
        recipe = get_object_or_404(Recipe, pk=recipe_id)
        try:
            data = json.loads(request.body)
            Comment.objects.create(recipe=recipe, text=data['comment'])
            return HttpResponse(status=201)
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({"error": "Invalid input"}, status=400)
    return HttpResponse("Method Not Allowed", status=405)

@csrf_exempt
def add_rating(request, recipe_id):
    if request.method == 'POST':
        recipe = get_object_or_404(Recipe, pk=recipe_id)
        try:
            data = json.loads(request.body)
            rating_val = data['rating']
            if not (1 <= rating_val <= 5):
                return JsonResponse({"error": "Rating must be between 1 and 5"}, status=400)
            Rating.objects.create(recipe=recipe, value=rating_val)
            return HttpResponse(status=201)
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({"error": "Invalid input"}, status=400)
    return HttpResponse("Method Not Allowed", status=405)