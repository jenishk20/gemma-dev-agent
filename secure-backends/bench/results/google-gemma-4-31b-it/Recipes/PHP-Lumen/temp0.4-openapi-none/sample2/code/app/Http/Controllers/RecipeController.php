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
        $recipes = Recipe::orderBy('id', 'desc')->take(10)->get();
        
        $html = "<h1>Recipe Overview</h1><ul>";
        foreach ($recipes as $recipe) {
            $html .= "<li><a href='/recipes/{$recipe->id}'>{$recipe->title}</a></li>";
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

        $recipe = Recipe::create($request->all());

        return response()->json([
            'id' => $recipe->id,
            'title' => $recipe->title,
            'ingredients' => $recipe->ingredients,
            'instructions' => $recipe->instructions,
            'comments' => [],
            'avgRating' => null
        ], 201);
    }

    public function show($recipeId)
    {
        $recipe = Recipe::with(['comments', 'ratings'])->find($recipeId);

        if (!$recipe) {
            return response('Recipe not found', 404);
        }

        $avgRating = $recipe->avg_rating ? round($recipe->avg_rating, 1) : 'No ratings yet';
        
        $html = "<h1>{$recipe->title}</h1>";
        $html .= "<h3>Ingredients</h3><ul>";
        foreach ($recipe->ingredients as $ing) {
            $html .= "<li>{$ing}</li>";
        }
        $html .= "</ul><h3>Instructions</h3><p>{$recipe->instructions}</p>";
        $html .= "<h3>Rating: {$avgRating}</h3>";
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
        if (!$recipe) return response()->json(['error' => 'Recipe not found'], 404);

        $validator = Validator::make($request->all(), [
            'comment' => 'required|string',
        ]);

        if ($validator->fails()) return response()->json(['error' => 'Invalid input'], 400);

        Comment::create([
            'recipe_id' => $recipeId,
            'comment' => $request->input('comment')
        ]);

        return response()->json([], 201);
    }

    public function addRating(Request $request, $recipeId)
    {
        $recipe = Recipe::find($recipeId);
        if (!$recipe) return response()->json(['error' => 'Recipe not found'], 404);

        $validator = Validator::make($request->all(), [
            'rating' => 'required|integer|min:1|max:5',
        ]);

        if ($validator->fails()) return response()->json(['error' => 'Invalid input'], 400);

        Rating::create([
            'recipe_id' => $recipeId,
            'rating' => $request->input('rating')
        ]);

        return response()->json([], 201);
    }
}