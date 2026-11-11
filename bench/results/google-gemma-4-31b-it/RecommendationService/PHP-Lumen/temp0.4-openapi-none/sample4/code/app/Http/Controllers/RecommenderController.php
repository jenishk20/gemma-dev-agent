<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Product;
use App\Models\Tag;
use Illuminate\Support\Facades\DB;

class RecommenderController extends Controller
{
    public function getProducts(Request $request)
    {
        $tagsQuery = $request->query('tags');
        if (!$tagsQuery) {
            return response('Missing tags parameter', 400);
        }

        $tagsArray = explode(',', $tagsQuery);
        
        $products = Product::whereHas('tags', function($query) use ($tagsArray) {
            $query->whereIn('name', $tagsArray);
        })->get();

        if ($products->isEmpty()) {
            return response('No products found matching the tags.', 200, ['Content-Type' => 'text/html']);
        }

        $html = "<ul>";
        foreach ($products as $product) {
            $html .= "<li>" . htmlspecialchars($product->product_name) . "</li>";
        }
        $html .= "</ul>";

        return response($html, 200, ['Content-Type' => 'text/html']);
    }

    public function storeProduct(Request $request)
    {
        $this->validate($request, [
            'product_name' => 'required|string',
            'tags' => 'required|array',
        ]);

        try {
            DB::transaction(function () use ($request) {
                $product = Product::create([
                    'product_name' => $request->input('product_name')
                ]);

                $tagIds = [];
                foreach ($request->input('tags') as $tagName) {
                    $tag = Tag::firstOrCreate(['name' => $tagName]);
                    $tagIds[] = $tag->id;
                }

                $product->tags()->sync($tagIds);
            });

            return response('Successful operation', 200);
        } catch (\Exception $e) {
            return response('Invalid input', 400);
        }
    }
}