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

# Safe evaluator using Abstract Syntax Trees (AST) to avoid eval()/exec()
# This prevents arbitrary code execution by only allowing specific arithmetic operations.
OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

def safe_eval(node):
    if isinstance(node, ast.Num):  # < Python 3.8
        return node.n
    elif isinstance(node, ast.Constant):  # >= Python 3.8
        if isinstance(node.value, (int, float)):
            return node.value
        raise TypeError(f"Unsupported constant type: {type(node.value)}")
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in OPERATORS:
            raise TypeError(f"Unsupported operator: {op_type}")
        return OPERATORS[op_type](safe_eval(node.left), safe_eval(node.right))
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in OPERATORS:
            raise TypeError(f"Unsupported operator: {op_type}")
        return OPERATORS[op_type](safe_eval(node.operand))
    else:
        raise TypeError(f"Unsupported expression node: {type(node)}")

@app.post("/calculator", response_model=CalculationResponse)
async def calculate(request: CalculationRequest):
    """
    Calculate the result of an arithmetic expression.
    """
    try:
        # Resource Exhaustion: Limit the length of the input expression to prevent CPU/Memory exhaustion
        if len(request.expression) > 1000:
            raise ValueError("Expression too long")

        # Parse the expression into an AST
        # mode='eval' ensures we are dealing with a single expression, not a script
        tree = ast.parse(request.expression, mode='eval')
        
        # Evaluate the AST safely
        result = safe_eval(tree.body)
        
        # Convert result to string as per schema requirement
        # Handle potential float precision or infinity/nan cases
        return CalculationResponse(result=str(result))
    except (SyntaxError, TypeError, ValueError, ZeroDivisionError, OverflowError):
        # Error Handling: Return 400 for any malformed or invalid arithmetic input
        # without leaking internal stack traces.
        raise HTTPException(status_code=400, detail="Invalid input")
    except Exception:
        # Catch-all for any other unexpected errors to ensure 400 is returned per spec
        raise HTTPException(status_code=400, detail="Invalid input")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)