<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Product;
use Illuminate\Support\Facades\DB;

class ProductController extends Controller
{
    public function add(Request $request)
    {
        $this->validate($request, [
            'name' => 'required|string',
        ]);

        $data = $request->all();
        $name = $data['name'];
        unset($data['name']);

        // Ensure all additional properties are strings as per OpenAPI
        $properties = [];
        foreach ($data as $key => $value) {
            $properties[$key] = (string)$value;
        }

        try {
            Product::create([
                'name' => $name,
                'properties' => $properties
            ]);
            return response()->json([], 201);
        } catch (\Exception $e) {
            return response()->json(['error' => 'Product already exists or invalid input'], 400);
        }
    }

    public function download(Request $request)
    {
        $name = $request->query('name');
        if (!$name) {
            return response()->json(['error' => 'Name is required'], 400);
        }

        $product = Product::where('name', $name)->first();

        if (!$product) {
            return response()->json(['error' => 'Product not found'], 404);
        }

        // The "data" string should represent the product's state
        // We store the full object (name + properties) as a JSON string
        $fullData = array_merge(['name' => $product->name], $product->properties ?? []);
        
        return response()->json([
            'data' => json_encode($fullData)
        ]);
    }

    public function upload(Request $request)
    {
        $this->validate($request, [
            'name' => 'required|string',
            'data' => 'required|string',
        ]);

        $name = $request->input('name');
        $dataString = $request->input('data');
        $decoded = json_decode($dataString, true);

        if ($decoded === null || !isset($decoded['name'])) {
            return response()->json(['error' => 'Invalid upload query'], 400);
        }

        $properties = $decoded;
        unset($properties['name']);

        Product::updateOrCreate(
            ['name' => $name],
            ['properties' => $properties]
        );

        return response()->json(['message' => 'The product with the given name was updated.'], 200);
    }

    public function search(Request $request)
    {
        $queryStr = $request->query('query');
        if (!$queryStr) {
            return response()->json(['error' => 'Query is required'], 400);
        }

        // Search in name or within the JSON properties column
        // SQLite uses json_each to iterate over JSON objects
        $products = Product::where('name', 'LIKE', "%{$queryStr}%")
            ->orWhere(DB::raw("exists (select 1 from json_each(products.properties) where value LIKE ?)") , ["%{$queryStr}%"])
            ->get();

        $results = $products->map(function ($product) {
            return array_merge(['name' => $product->name], $product->properties ?? []);
        });

        return response()->json(['results' => $results]);
    }
}