<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Product;
use Illuminate\Support\Facades\Validator;

class ProductController extends Controller
{
    public function add(Request $request)
    {
        $validator = Validator::make($request->all(), [
            'name' => 'required|string',
        ]);

        if ($validator->fails()) {
            return response()->json(['error' => 'Invalid input'], 400);
        }

        $data = $request->all();
        $name = $data['name'];
        unset($data['name']);

        // Ensure all additional properties are strings as per OpenAPI spec
        foreach ($data as $key => $value) {
            if (!is_string($value)) {
                return response()->json(['error' => 'Additional properties must be strings'], 400);
            }
        }

        Product::updateOrCreate(
            ['name' => $name],
            ['properties' => $data]
        );

        return response()->json([], 201);
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

        // The "data" string should represent the product's state (name + properties)
        // To allow /upload to replace it, we store the full object as a JSON string
        $fullData = array_merge(['name' => $product->name], $product->properties);
        
        return response()->json([
            'data' => json_encode($fullData)
        ]);
    }

    public function upload(Request $request)
    {
        $validator = Validator::make($request->all(), [
            'name' => 'required|string',
            'data' => 'required|string',
        ]);

        if ($validator->fails()) {
            return response()->json(['error' => 'Invalid upload query'], 400);
        }

        $decodedData = json_decode($request->input('data'), true);
        if (json_last_error() !== JSON_ERROR_NONE || !is_array($decodedData)) {
            return response()->json(['error' => 'Invalid data format'], 400);
        }

        $name = $request->input('name');
        
        // The spec says "fully replaces any previous data for the product"
        // We extract the name and treat the rest as properties
        $properties = $decodedData;
        unset($properties['name']);

        Product::updateOrCreate(
            ['name' => $name],
            ['properties' => $properties]
        );

        return response()->json(['message' => 'The product with the given name was updated.'], 200);
    }

    public function search(Request $request)
    {
        $query = $request->query('query');
        if (!$query) {
            return response()->json(['error' => 'Invalid search query'], 400);
        }

        // Search in name or within the JSON properties column
        $products = Product::where('name', 'LIKE', "%$query%")
            ->orWhere('properties', 'LIKE', "%$query%")
            ->get();

        $results = $products->map(function ($product) {
            return array_merge(['name' => $product->name], $product->properties);
        });

        return response()->json(['results' => $results]);
    }
}