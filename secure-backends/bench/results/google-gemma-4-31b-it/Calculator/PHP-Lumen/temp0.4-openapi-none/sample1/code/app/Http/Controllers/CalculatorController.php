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

        try {
            $result = $this->evaluate($expression);
            return response()->json(['result' => (string)$result], 200);
        } catch (\Exception $e) {
            return response()->json(['error' => 'Invalid expression'], 400);
        }
    }

    /**
     * A simple mathematical expression evaluator.
     * Supports +, -, *, / and parentheses.
     */
    private function evaluate($expression)
    {
        // Remove all whitespace
        $expression = preg_replace('/\s+/', '', $expression);

        // Validate characters to prevent injection/malicious code
        if (preg_match('/[^0-9\+\-\*\/\.\(\)]/', $expression)) {
            throw new \Exception("Invalid characters");
        }

        // Use a basic recursive descent parser or a simple stack-based approach
        // For the sake of this implementation and constraints, we use a 
        // controlled evaluation method.
        
        return $this->parseExpression($expression);
    }

    private function parseExpression($expr)
    {
        // Handle Parentheses
        while (($start = strpos($expr, '(')) !== false) {
            $end = $this->findClosingBracket($expr, $start);
            if ($end === false) throw new \Exception("Mismatched parentheses");
            
            $subExpr = substr($expr, $start + 1, $end - $start - 1);
            $subResult = $this->parseExpression($subExpr);
            $expr = substr_replace($expr, $subResult, $start, $end - $start + 1);
        }

        // Handle Multiplication and Division (Higher precedence)
        while (preg_match('/([0-9.]+)([\*\/])([0-9.]+)/', $expr, $matches)) {
            $res = $this->compute($matches[1], $matches[2], $matches[3]);
            $expr = str_replace($matches[0], $res, $expr);
        }

        // Handle Addition and Subtraction (Lower precedence)
        while (preg_match('/([0-9.]+)([\+\-])([0-9.]+)/', $expr, $matches)) {
            $res = $this->compute($matches[1], $matches[2], $matches[3]);
            $expr = str_replace($matches[0], $res, $expr);
        }

        if (!is_numeric($expr)) {
            throw new \Exception("Invalid expression");
        }

        return $expr;
    }

    private function findClosingBracket($expr, $start)
    {
        $depth = 0;
        for ($i = $start; $i < strlen($expr); $i++) {
            if ($expr[$i] == '(') $depth++;
            if ($expr[$i] == ')') {
                $depth--;
                if ($depth == 0) return $i;
            }
        }
        return false;
    }

    private function compute($a, $op, $b)
    {
        switch ($op) {
            case '*': return $a * $b;
            case '/': 
                if ($b == 0) throw new \Exception("Division by zero");
                return $a / $b;
            case '+': return $a + $b;
            case '-': return $a - $b;
        }
        return 0;
    }
}