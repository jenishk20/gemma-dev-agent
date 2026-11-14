<?php

namespace App\Http\Controllers;

use App\Models\Recipe;
use App\Models\Comment;
use App\Models\Rating;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Validator;

class RecipeController extends Controller
{
    public function index()
    {
        $recipes = Recipe::with('ratings')->orderByDesc('created_at')->take(10)->get();
        
        $html = "<h1>Recent Recipes</h1><ul>";
        foreach ($recipes as $recipe) {
            $html .= "<li><a href='/recipes/{$recipe->id}'>{$recipe->title}</a> (Rating: " . number_format($recipe->avg_rating, 1) . ")</li>";
        }
        $html .= "</ul>";

        return response($html, 200)->header('Content-Type', 'text/html');
    }

    public function store(Request $request)
    {
        $validator = Validator::make($request->all(), [
            'title' => 'required|string',
            'ingredients' => 'required|array',
            'instructions' => 'required|string',
        ]);

        if ($validator->fails()) {
            return response()->json(['error' => 'Invalid input'], 400);
        }

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
            return response()->json(['error' => 'Recipe not found'], 404);
        }

        $avgRating = number_format($recipe->avg_rating, 1);
        $commentsHtml = "<h3>Comments</h3><ul>";
        foreach ($recipe->comments as $comment) {
            $commentsHtml .= "<li>{$comment->comment}</li>";
        }
        $commentsHtml .= "</ul>";

        $html = "<h1>{$recipe->title}</h1>";
        $html .= "<h3>Ingredients</h3><ul>";
        foreach ($recipe->ingredients as $ing) {
            $html .= "<li>{$ing}</li>";
        }
        $html .= "</ul>";
        $html .= "<h3>Instructions</h3><p>{$recipe->instructions}</p>";
        $html .= "<h3>Average Rating: {$avgRating}/5</h3>";
        $html .= $commentsHtml;

        return response($html, 200)->header('Content-Type', 'text/html');
    }

    public function addComment(Request $request, $recipeId)
    {
        $recipe = Recipe::find($recipeId);
        if (!$recipe) {
            return response()->json(['error' => 'Recipe not found'], 404);
        }

        $validator = Validator::make($request->all(), [
            'comment' => 'required|string',
        ]);

        if ($validator->fails()) {
            return response()->json(['error' => 'Invalid input'], 400);
        }

        Comment::create([
            'recipe_id' => $recipeId,
            'comment' => $request->comment,
        ]);

        return response()->json(['message' => 'Comment added successfully'], 201);
    }

    public function addRating(Request $request, $recipeId)
    {
        $recipe = Recipe::find($recipeId);
        if (!$recipe) {
            return response()->json(['error' => 'Recipe not found'], 404);
        }

        $validator = Validator::make($request->all(), [
            'rating' => 'required|integer|min:1|max:5',
        ]);

        if ($validator->fails()) {
            return response()->json(['error' => 'Invalid input'], 400);
        }

        Rating::create([
            'recipe_id' => $recipeId,
            'rating' => $request->rating,
        ]);

        return response()->json(['message' => 'Rating added successfully'], 201);
    }
}