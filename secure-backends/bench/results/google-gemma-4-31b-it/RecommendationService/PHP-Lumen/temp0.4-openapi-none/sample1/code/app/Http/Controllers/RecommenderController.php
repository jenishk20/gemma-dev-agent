<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Product;
use App\Models\Tag;
use Illuminate\Support\Facades\DB;

class RecommenderController extends Controller
{
    public function getRecommendations(Request $request)
    {
        $tagsQuery = $request->query('tags');

        if (!$tagsQuery) {
            return response('Missing tags parameter', 400);
        }

        $tagsArray = explode(',', $tagsQuery);
        
        // Find products that have at least one of the provided tags
        $products = Product::whereHas('tags', function($query) use ($tagsArray) {
            $query->whereIn('name', $tagsArray);
        })->get();

        if ($products->isEmpty()) {
            return response('No products found matching the tags.', 200)->header('Content-Type', 'text/html');
        }

        $html = "<html><body><h1>Recommended Products</h1><ul>";
        foreach ($products as $product) {
            $html .= "<li>" . htmlspecialchars($product->product_name) . "</li>";
        }
        $html .= "</ul></body></html>";

        return response($html, 200)->header('Content-Type', 'text/html');
    }

    public function storeProduct(Request $request)
    {
        $this->validate($request, [
            'product_name' => 'required|string',
            'tags' => 'required|array',
        ]);

        $productName = $request->input('product_name');
        $tagsInput = $request->input('tags');

        try {
            DB::transaction(function () use ($productName, $tagsInput) {
                $product = Product::create(['product_name' => $productName]);
                
                foreach ($tagsInput as $tagName) {
                    $tag = Tag::firstOrCreate(['name' => $tagName]);
                    $product->tags()->attach($tag->id);
                }
            });

            return response('Successful operation', 200);
        } catch (\Exception $e) {
            return response('Invalid input', 400);
        }
    }
}