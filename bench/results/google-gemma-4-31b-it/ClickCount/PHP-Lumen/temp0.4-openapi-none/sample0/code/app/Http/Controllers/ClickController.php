<?php

namespace App\Http\Controllers;

use App\Models\Click;
use Illuminate\Http\Request;
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
            return response()->json(['error' => 'Invalid request'], 400);
        }

        $date = $request->input('date');
        $direction = $request->input('direction');

        // We filter by the date. Since the DB stores full timestamps, 
        // we compare against the start/end of the provided date.
        $clicks = Click::where('timestamp', $direction, $date)->get();

        if ($clicks->isEmpty()) {
            return response()->json(['error' => 'No clicks found'], 404);
        }

        return response()->json($clicks, 200);
    }
}