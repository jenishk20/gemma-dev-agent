<?php

namespace App\Http\Controllers;

use App\Models\Recipe;
use App\Models\Comment;
use App\Models\Rating;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

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
        return response($html)->header('Content-Type', 'text/html');
    }

    public function store(Request $request)
    {
        $this->validate($request, [
            'title' => 'required|string',
            'ingredients' => 'required|array',
            'instructions' => 'required|string',
        ]);

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

    public function show($id)
    {
        $recipe = Recipe::with(['comments', 'ratings'])->find($id);
        if (!$recipe) return response()->json(['error' => 'Not Found'], 404);

        $avgRating = $recipe->avg_rating;
        $comments = $recipe->comments->pluck('comment');
        
        $html = "<h1>{$recipe->title}</h1>";
        $html .= "<h3>Ingredients</h3><ul>";
        foreach($recipe->ingredients as $ing) $html .= "<li>$ing</li>";
        $html .= "</ul><h3>Instructions</h3><p>{$recipe->instructions}</p>";
        $html .= "<h3>Average Rating: $avgRating</h3>";
        $html .= "<h3>Comments</h3><ul>";
        foreach($comments as $c) $html .= "<li>$c</li>";
        $html .= "</ul>";

        return response($html)->header('Content-Type', 'text/html');
    }

    public function addComment(Request $request, $id)
    {
        $recipe = Recipe::find($id);
        if (!$recipe) return response()->json(['error' => 'Not Found'], 404);

        $this->validate($request, ['comment' => 'required|string']);

        Comment::create([
            'recipe_id' => $id,
            'comment' => $request->input('comment')
        ]);

        return response()->json([], 201);
    }

    public function addRating(Request $request, $id)
    {
        $recipe = Recipe::find($id);
        if (!$recipe) return response()->json(['error' => 'Not Found'], 404);

        $this->validate($request, ['rating' => 'required|integer|min:1|max:5']);

        Rating::create([
            'recipe_id' => $id,
            'rating' => $request->input('rating')
        ]);

        return response()->json([], 201);
    }
}