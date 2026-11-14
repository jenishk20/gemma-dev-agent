<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Product;
use App\Models\Tag;
use Illuminate\Support\Facades\DB;

class RecommenderController extends Controller
{
    public function index(Request $request)
    {
        $tagsQuery = $request->query('tags');
        if (!$tagsQuery) {
            return response('Missing tags parameter', 400);
        }

        $tagsArray = explode(',', $tagsQuery);
        
        $products = Product::whereHas('tags', function ($query) use ($tagsArray) {
            $query->whereIn('name', $tagsArray);
        })->get();

        if ($products->isEmpty()) {
            return response('', 200)->header('Content-Type', 'text/html');
        }

        $html = "<ul>";
        foreach ($products as $product) {
            $html .= "<li>" . htmlspecialchars($product->product_name) . "</li>";
        }
        $html .= "</ul>";

        return response($html, 200)->header('Content-Type', 'text/html');
    }

    public function store(Request $request)
    {
        $this->validate($request, [
            'product_name' => 'required|string',
            'tags' => 'required|array',
            'tags.*' => 'string'
        ]);

        $productName = $request->input('product_name');
        $tagsInput = $request->input('tags');

        $product = DB::transaction(function () use ($productName, $tagsInput) {
            $product = Product::create(['product_name' => $productName]);
            
            foreach ($tagsInput as $tagName) {
                $tag = Tag::firstOrCreate(['name' => $tagName]);
                $product->tags()->attach($tag->id);
            }
            
            return $product;
        });

        return response()->json(['message' => 'Successful operation'], 200);
    }
}