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
            // We use a basic mathematical evaluation. 
            // In a production environment, a proper parser library is recommended.
            // Here we use a controlled eval for the sake of the exercise.
            $result = $this->evaluate($expression);
            
            return response()->json([
                'result' => (string)$result
            ], 200);
        } catch (\Throwable $e) {
            return response()->json(['error' => 'Invalid expression'], 400);
        }
    }

    private function evaluate($expression)
    {
        // Remove all whitespace
        $expression = str_replace(' ', '', $expression);
        
        // Use a simple approach to evaluate the math string
        // Note: eval is used here only after strict regex validation above
        return eval("return $expression;");
    }
}