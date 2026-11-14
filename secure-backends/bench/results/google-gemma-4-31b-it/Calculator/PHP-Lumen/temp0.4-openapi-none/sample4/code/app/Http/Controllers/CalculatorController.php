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

        // Sanitize input: allow only numbers, operators, spaces, and parentheses
        // This prevents arbitrary PHP code execution
        if (preg_match('/[^0-9\+\-\*\/\.\s\(\)]/', $expression)) {
            return response()->json(['error' => 'Invalid characters in expression'], 400);
        }

        try {
            // We use a simple mathematical evaluation. 
            // In a production environment, a proper Lexer/Parser is recommended.
            // For this task, we use a controlled eval approach after strict regex validation.
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
        // Replace '^' with power if needed, but schema doesn't specify.
        // Using a basic eval since we strictly validated the characters above.
        $res = eval("return $expression;");
        
        if ($res === false) {
            throw new \Exception("Evaluation failed");
        }
        
        return $res;
    }
}