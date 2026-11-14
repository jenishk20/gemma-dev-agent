<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Recipe;
use App\Models\Comment;
use App\Models\Rating;

class RecipeController extends Controller
{
    public function index()
    {
        $recipes = Recipe::orderBy('id', 'desc')->limit(10)->get();
        $html = "<h1>Recipe Overview</h1><ul>";
        foreach ($recipes as $recipe) {
            $html .= "<li><a href='/recipes/{$recipe->id}'>{$recipe->title}</a> (Rating: {$recipe->avg_rating})</li>";
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

    public function show($id)
    {
        $recipe = Recipe::with(['comments', 'ratings'])->find($id);
        if (!$recipe) return response('Recipe not found', 404);

        $commentsHtml = "<h3>Comments</h3><ul>";
        foreach ($recipe->comments as $c) {
            $commentsHtml .= "<li>{$c->comment}</li>";
        }
        $commentsHtml .= "</ul>";

        $html = "<h1>{$recipe->title}</h1>";
        $html .= "<h3>Ingredients</h3><ul>";
        foreach ($recipe->ingredients as $ing) {
            $html .= "<li>{$ing}</li>";
        }
        $html .= "</ul>";
        $html .= "<h3>Instructions</h3><p>{$recipe->instructions}</p>";
        $html .= "<h3>Average Rating: {$recipe->avg_rating}</h3>";
        $html .= $commentsHtml;

        return response($html, 200)->header('Content-Type', 'text/html');
    }

    public function addComment(Request $request, $id)
    {
        $recipe = Recipe::find($id);
        if (!$recipe) return response()->json(['error' => 'Recipe not found'], 404);

        $this->validate($request, ['comment' => 'required|string']);

        Comment::create([
            'recipe_id' => $id,
            'comment' => $request->comment
        ]);

        return response()->json(['message' => 'Comment added'], 201);
    }

    public function addRating(Request $request, $id)
    {
        $recipe = Recipe::find($id);
        if (!$recipe) return response()->json(['error' => 'Recipe not found'], 404);

        $this->validate($request, ['rating' => 'required|integer|min:1|max:5']);

        Rating::create([
            'recipe_id' => $id,
            'rating' => $request->rating
        ]);

        return response()->json(['message' => 'Rating added'], 201);
    }
}