<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Product;
use Illuminate\Support\Facades\DB;

class ProductController extends Controller
{
    public function __construct()
    {
        // Ensure table exists for this demo since we aren't running migrations manually
        if (!DB::getSchemaBuilder()->hasTable('products')) {
            DB::statement('CREATE TABLE products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, properties TEXT, created_at DATETIME, updated_at DATETIME)');
            DB::statement('CREATE INDEX idx_product_name ON products(name)');
        }
    }

    public function add(Request $request)
    {
        $this->validate($request, [
            'name' => 'required|string',
        ]);

        $data = $request->all();
        $name = $data['name'];
        unset($data['name']);

        // All other fields are treated as unstructured properties
        $properties = [];
        foreach ($data as $key => $value) {
            if (is_string($value)) {
                $properties[$key] = $value;
            }
        }

        Product::create([
            'name' => $name,
            'properties' => $properties
        ]);

        return response()->json([], 201);
    }

    public function download(Request $request)
    {
        $this->validate($request, [
            'name' => 'required|string',
        ]);

        $product = Product::where('name', $request->query('name'))->first();

        if (!$product) {
            return response()->json(['error' => 'Product not found'], 404);
        }

        // Combine name and properties into a single object, then stringify for the 'data' field
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

        $decodedData = json_decode($request->input('data'), true);

        if (json_last_error() !== JSON_ERROR_NONE || !is_array($decodedData)) {
            return response()->json(['error' => 'Invalid data format'], 400);
        }

        $name = $decodedData['name'] ?? null;
        if (!$name || $name !== $request->input('name')) {
            return response()->json(['error' => 'Data name mismatch'], 400);
        }

        unset($decodedData['name']);

        $product = Product::where('name', $name)->first();
        
        if ($product) {
            $product->update(['properties' => $decodedData]);
        } else {
            Product::create([
                'name' => $name,
                'properties' => $decodedData
            ]);
        }

        return response()->json(['message' => 'Product updated successfully'], 200);
    }

    public function search(Request $request)
    {
        $this->validate($request, [
            'query' => 'required|string',
        ]);

        $query = $request->query('query');
        
        // Search in name OR within the JSON properties column
        $products = Product::where('name', 'LIKE', "%$query%")
            ->orWhere('properties', 'LIKE', "%$query%")
            ->get();

        $results = $products->map(function ($product) {
            return array_merge(['name' => $product->name], $product->properties ?? []);
        });

        return response()->json(['results' => $results]);
    }
}