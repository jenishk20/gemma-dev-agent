import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import ast
import operator

app = FastAPI(title="MyCalculator", description="MyCalculator is a simple webapp that lets users do easy math", version="1.0.11")

class CalculationRequest(BaseModel):
    expression: str

class CalculationResponse(BaseModel):
    result: str

# Define allowed operators for the safe evaluator
OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

def safe_eval(node):
    """
    Recursively evaluate an AST node. 
    This replaces eval() to prevent arbitrary code execution.
    """
    if isinstance(node, ast.Num):  # < Python 3.8
        return node.n
    elif isinstance(node, ast.Constant):  # >= Python 3.8
        if isinstance(node.value, (int, float)):
            return node.value
        raise TypeError("Unsupported constant type")
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type in OPERATORS:
            left = safe_eval(node.left)
            right = safe_eval(node.right)
            # Prevent resource exhaustion via massive exponents (e.g., 10**1000000)
            if op_type == ast.Pow:
                if right > 1000 or left > 1000: # Reasonable limit for a simple calculator
                    raise ValueError("Exponent too large")
            return OPERATORS[op_type](left, right)
        raise TypeError(f"Unsupported operator: {op_type}")
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type in OPERATORS:
            return OPERATORS[op_type](safe_eval(node.operand))
        raise TypeError(f"Unsupported unary operator: {op_type}")
    else:
        raise TypeError(f"Unsupported expression element: {type(node)}")

@app.post("/calculator", response_model=CalculationResponse)
async def calculate(request: CalculationRequest):
    """
    Calculate the result of an arithmetic expression.
    """
    expression = request.expression
    
    # Resource exhaustion: Bound the length of the input string
    if len(expression) > 1000:
        raise HTTPException(status_code=400, detail="Invalid input: Expression too long")

    try:
        # Parse the expression into an Abstract Syntax Tree (AST)
        # ast.parse is safe as it doesn't execute code, it only analyzes it.
        tree = ast.parse(expression, mode='eval')
        
        # Evaluate the AST using our restricted safe_eval function
        # This ensures no built-ins, imports, or arbitrary function calls are executed.
        res = safe_eval(tree.body)
        
        # Ensure result is a number before converting to string
        if not isinstance(res, (int, float)):
            raise TypeError("Result is not a number")
            
        return CalculationResponse(result=str(res))
    except (SyntaxError, TypeError, ValueError, ZeroDivisionError, OverflowError):
        # Return 400 for any malformed input or math errors as per OpenAPI spec
        raise HTTPException(status_code=400, detail="Invalid input")
    except Exception:
        # Catch-all to prevent leaking internal stack traces
        raise HTTPException(status_code=400, detail="Invalid input")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)