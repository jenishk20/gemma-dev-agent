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
    Recursively evaluate an AST node to ensure only basic math is performed.
    This replaces eval() to prevent arbitrary code execution.
    """
    if isinstance(node, ast.Num):  # < Python 3.8
        return node.n
    elif isinstance(node, ast.Constant):  # Python 3.8+
        if isinstance(node.value, (int, float)):
            return node.value
        raise TypeError(f"Unsupported constant type: {type(node.value)}")
    elif isinstance(node, ast.BinOp):
        left = safe_eval(node.left)
        right = safe_eval(node.right)
        op_type = type(node.op)
        if op_type not in OPERATORS:
            raise TypeError(f"Unsupported operator: {op_type}")
        # Prevent resource exhaustion via extremely large exponents
        if op_type == ast.Pow:
            if left > 1000 or right > 1000:
                raise ValueError("Exponent too large")
        return OPERATORS[op_type](left, right)
    elif isinstance(node, ast.UnaryOp):
        operand = safe_eval(node.operand)
        op_type = type(node.op)
        if op_type not in OPERATORS:
            raise TypeError(f"Unsupported operator: {op_type}")
        return OPERATORS[op_type](operand)
    else:
        raise TypeError(f"Unsupported expression element: {type(node)}")

@app.post("/calculator", response_model=CalculationResponse)
async def calculate(request: CalculationRequest):
    """
    Calculate the result of an arithmetic expression.
    """
    expression = request.expression
    
    # Basic input validation for length to prevent resource exhaustion (DoS)
    if len(expression) > 500:
        raise HTTPException(status_code=400, detail="Invalid input: Expression too long")

    try:
        # Parse the expression into an Abstract Syntax Tree (AST)
        # mode='eval' ensures only a single expression is parsed
        tree = ast.parse(expression, mode='eval')
        
        # Evaluate the AST safely
        result_val = safe_eval(tree.body)
        
        # Convert result to string as per schema
        return CalculationResponse(result=str(result_val))
    except (SyntaxError, TypeError, ValueError, ZeroDivisionError, OverflowError):
        # Catch all parsing and evaluation errors and return 400 as per schema
        raise HTTPException(status_code=400, detail="Invalid input")
    except Exception:
        # Generic catch-all to prevent leaking internal stack traces
        raise HTTPException(status_code=400, detail="Invalid input")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)