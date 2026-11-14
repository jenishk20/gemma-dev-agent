<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Click;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\Validator;

class ClickController extends Controller
{
    public function store(Request $request)
    {
        // Register a click with the current timestamp
        $click = Click::create([
            'timestamp' => Carbon::now()
        ]);

        return response()->json($click, 201);
    }

    public function index(Request $request)
    {
        $validator = Validator::make($request->all(), [
            'date' => 'required|date_format:Y-m-d',
            'direction' => 'required|in:<,>,<=,>=',
        ]);

        if ($validator->fails()) {
            return response()->json(['error' => 'Invalid request parameters'], 400);
        }

        $date = $request->query('date');
        $direction = $request->query('direction');

        // We filter by the date. Since timestamp is datetime, 
        // we compare the date part or the start/end of the day depending on the operator.
        $clicks = Click::where('timestamp', $direction, $date)->get();

        if ($clicks->isEmpty()) {
            return response()->json(['message' => 'No clicks found'], 404);
        }

        return response()->json($clicks, 200);
    }
}