<?php

namespace App\Http\Controllers;

use App\Models\Recipe;
use App\Models\Comment;
use App\Models\Rating;
use Illuminate\Http\Request;

class RecipeController extends Controller
{
    public function index()
    {
        $recipes = Recipe::all();
        $html = "<h1>Recipe Overview</h1><ul>";
        foreach ($recipes as $recipe) {
            $html .= "<li><a href='/recipes/{$recipe->id}'>{$recipe->title}</a></li>";
        }
        $html .= "</ul>";
        return response($html, 200)->header('Content-Type', 'text/html');
    }

    public function store(Request $request)
    {
        $this->validate($request, [
            'title' => 'required|string',
            'ingredients' => 'required|array',
            'instructions' => 'required|string',
        ]);

        $recipe = Recipe::create([
            'title' => $request->title,
            'ingredients' => $request->ingredients,
            'instructions' => $request->instructions,
        ]);

        return response()->json($recipe, 201);
    }

    public function show($recipeId)
    {
        $recipe = Recipe::with(['comments', 'ratings'])->find($recipeId);

        if (!$recipe) {
            return response('Recipe not found', 404);
        }

        $avgRating = $recipe->avg_rating ? round($recipe->avg_rating, 1) : 'No ratings';
        
        $html = "<h1>{$recipe->title}</h1>";
        $html .= "<h3>Ingredients</h3><ul>";
        foreach ($recipe->ingredients as $ing) {
            $html .= "<li>{$ing}</li>";
        }
        $html .= "</ul><h3>Instructions</h3><p>{$recipe->instructions}</p>";
        $html .= "<h3>Average Rating: {$avgRating}</h3>";
        $html .= "<h3>Comments</h3><ul>";
        foreach ($recipe->comments as $comment) {
            $html .= "<li>{$comment->comment}</li>";
        }
        $html .= "</ul>";

        return response($html, 200)->header('Content-Type', 'text/html');
    }

    public function addComment(Request $request, $recipeId)
    {
        $recipe = Recipe::find($recipeId);
        if (!$recipe) return response()->json(['error' => 'Not found'], 404);

        $this->validate($request, ['comment' => 'required|string']);

        Comment::create([
            'recipe_id' => $recipeId,
            'comment' => $request->comment
        ]);

        return response()->json(['message' => 'Comment added'], 201);
    }

    public function addRating(Request $request, $recipeId)
    {
        $recipe = Recipe::find($recipeId);
        if (!$recipe) return response()->json(['error' => 'Not found'], 404);

        $this->validate($request, ['rating' => 'required|integer|min:1|max:5']);

        Rating::create([
            'recipe_id' => $recipeId,
            'rating' => $request->rating
        ]);

        return response()->json(['message' => 'Rating added'], 201);
    }
}