<?php

namespace App\Http\Controllers;

use App\Models\Click;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Validator;

class ClickController extends Controller
{
    public function store(Request $request)
    {
        try {
            $click = Click::create([
                'timestamp' => now()
            ]);
            return response()->json($click, 201);
        } catch (\Exception $e) {
            return response()->json(['error' => 'Invalid request'], 400);
        }
    }

    public function index(Request $request)
    {
        $validator = Validator::make($request->all(), [
            'date' => 'required|date_format:Y-m-d',
            'direction' => 'required|in:<,>,<=,>=',
        ]);

        if ($validator->fails()) {
            return response()->json(['error' => 'Invalid request'], 400);
        }

        $date = $request->query('date');
        $direction = $request->query('direction');

        $clicks = Click::where('timestamp', $direction, $date)->get();

        if ($clicks->isEmpty()) {
            return response()->json(['error' => 'No clicks found'], 404);
        }

        return response()->json($clicks, 200);
    }
}