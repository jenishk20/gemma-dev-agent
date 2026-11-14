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
        
        // Find products that have at least one of the requested tags
        $products = Product::whereHas('tags', function($q) use ($tagsArray) {
            $q->whereIn('name', $tagsArray);
        })->get();

        if ($products->isEmpty()) {
            return response('No products found matching these tags.', 200, ['Content-Type' => 'text/html']);
        }

        $html = "<html><body><h1>Recommended Products</h1><ul>";
        foreach ($products as $product) {
            $html .= "<li>" . htmlspecialchars($product->product_name) . "</li>";
        }
        $html .= "</ul></body></html>";

        return response($html, 200)->header('Content-Type', 'text/html');
    }

    public function store(Request $request)
    {
        $this->validate($request, [
            'product_name' => 'required|string',
            'tags' => 'required|array',
            'tags.*' => 'string'
        ]);

        DB::transaction(function () use ($request) {
            $product = Product::create(['product_name' => $request->input('product_name')]);
            
            $tagIds = [];
            foreach ($request->input('tags') as $tagName) {
                $tag = Tag::firstOrCreate(['name' => $tagName]);
                $tagIds[] = $tag->id;
            }
            
            $product->tags()->attach($tagIds);
        });

        return response('Successful operation', 200);
    }
}