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

        // Sanitize input: allow only numbers, basic operators, spaces, and parentheses
        // This prevents arbitrary PHP code execution
        if (preg_match('/[^0-9\+\-\*\/\.\s\(\)]/', $expression)) {
            return response()->json(['error' => 'Invalid characters in expression'], 400);
        }

        try {
            // We use a simple approach to evaluate the expression.
            // Since we have strictly sanitized the input to only contain math characters,
            // we can safely use a basic evaluation logic.
            $result = $this->evaluate($expression);
            
            return response()->json([
                'result' => (string)$result
            ], 200);
        } catch (\Exception $e) {
            return response()->json(['error' => 'Invalid expression'], 400);
        }
    }

    private function evaluate($expression)
    {
        // Remove spaces
        $expression = str_replace(' ', '', $expression);
        
        // Using a basic approach for math evaluation. 
        // In a production environment, a proper Lexer/Parser would be used.
        // Given the constraints and the sanitized input, we can use a safe eval-like 
        // approach or a manual calculation.
        
        // We use a trick to evaluate the math string safely after strict regex validation.
        $result = 0;
        // create a function to handle the math
        $calc = function($expr) {
            // This is safe because the regex in the controller 
            // stripped everything except digits and math operators.
            return eval("return $expr;");
        };

        return $calc($expression);
    }
}