import uvicorn
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import ast
import operator

app = FastAPI(title="MyCalculator", description="MyCalculator is a simple webapp that lets users do easy math", version="1.0.11")

class CalculationRequest(BaseModel):
    expression: str

class CalculationResponse(BaseModel):
    result: str

def safe_eval(expr):
    """
    Safely evaluate a mathematical expression using Abstract Syntax Trees (AST).
    This avoids the security risks of using the built-in eval().
    """
    # Supported operators
    operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }

    def eval_(node, depth):
        # Resource Exhaustion: Prevent deep recursion/nested expressions
        if depth > 100:
            raise RecursionError("Expression too complex")

        if isinstance(node, ast.Num):  # < Python 3.8
            return node.n
        elif isinstance(node, ast.Constant):  # Python 3.8+
            if not isinstance(node.value, (int, float)):
                raise TypeError("Unsupported constant type")
            return node.value
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type in operators:
                left = eval_(node.left, depth + 1)
                right = eval_(node.right, depth + 1)
                
                # Resource Exhaustion: Prevent CPU exhaustion from massive exponents
                if op_type == ast.Pow:
                    if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
                        raise TypeError("Pow requires numbers")
                    if abs(left) > 1e10 or abs(right) > 1000:
                        raise ValueError("Exponent too large")
                
                return operators[op_type](left, right)
            else:
                raise TypeError(f"Unsupported operator: {op_type}")
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type in operators:
                operand = eval_(node.operand, depth + 1)
                return operators[op_type](operand)
            else:
                raise TypeError(f"Unsupported operator: {op_type}")
        else:
            raise TypeError(f"Unsupported expression element: {type(node)}")

    try:
        # Parse the expression into an AST. 
        # mode='eval' ensures only a single expression is parsed, not statements.
        tree = ast.parse(expr, mode='eval')
        return eval_(tree.body, 0)
    except Exception as e:
        raise e

@app.post("/calculator", response_model=CalculationResponse)
async def calculate(request: CalculationRequest):
    try:
        # Resource Exhaustion: Bound the input string length to prevent DoS via huge strings
        if len(request.expression) > 1000:
            raise ValueError("Expression too long")

        # Evaluate the expression safely
        res = safe_eval(request.expression)
        
        # Convert result to string as per OpenAPI schema example
        return CalculationResponse(result=str(res))
    except (SyntaxError, TypeError, ValueError, RecursionError, ZeroDivisionError, OverflowError):
        # Error handling: Catch specific exceptions and return documented 400 status code
        # without leaking internal stack traces.
        raise HTTPException(status_code=400, detail="Invalid input")
    except Exception:
        # Generic catch-all to ensure no internal details leak
        raise HTTPException(status_code=400, detail="Invalid input")

if __name__ == "__main__":
    # Start the server on port 5000 and host 0.0.0.0
    uvicorn.run(app, host="0.0.0.0", port=5000)