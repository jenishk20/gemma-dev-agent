<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Validator;

class CalculatorController extends Controller
{
    public function calculate(Request $request)
    {
        $validator = Validator::make($request->all(), [
            'expression' => 'required|string',
        ]);

        if ($validator->fails()) {
            return response()->json(['error' => 'Invalid input'], 400);
        }

        $expression = $request->input('expression');

        // Security: Only allow numbers, basic operators, spaces, and parentheses
        if (preg_match('/[^0-9\+\-\*\/\.\s\(\)]/', $expression)) {
            return response()->json(['error' => 'Invalid characters in expression'], 400);
        }

        try {
            // We use a basic approach to evaluate the expression.
            // In a production environment, a proper parser library is recommended.
            // Here we use a sanitized eval for the purpose of the exercise.
            $result = eval("return " . $expression . ";");
            
            if (!is_numeric($result)) {
                throw new \Exception("Invalid result");
            }

            return response()->json([
                'result' => (string)$result
            ], 200);
        } catch (\Throwable $e) {
            return response()->json(['error' => 'Invalid expression'], 400);
        }
    }
}