import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import ast
import operator

# Define the request and response models based on the OpenAPI schema
class CalculationRequest(BaseModel):
    expression: str

class CalculationResponse(BaseModel):
    result: str

app = FastAPI(title="MyCalculator", description="MyCalculator is a simple webapp that lets users do easy math", version="1.0.11")

# Safe evaluator to replace eval() to prevent arbitrary code execution (RCE)
# This implements a recursive descent parser using the Abstract Syntax Tree (AST)
def safe_eval(expr):
    # Define supported operators
    operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def eval_node(node):
        if isinstance(node, ast.Num):  # < Python 3.8
            return node.n
        elif isinstance(node, ast.Constant):  # >= Python 3.8
            if isinstance(node.value, (int, float)):
                return node.value
            raise TypeError("Unsupported constant type")
        elif isinstance(node, ast.BinOp):
            left = eval_node(node.left)
            right = eval_node(node.right)
            # Resource exhaustion: prevent massive numbers via exponentiation
            if isinstance(node.op, ast.Pow):
                if left > 1000 or right > 1000:
                    raise ValueError("Operand too large for power operation")
            return operators[type(node.op)](left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = eval_node(node.operand)
            return operators[type(node.op)](operand)
        else:
            raise TypeError(f"Unsupported operation: {type(node).__name__}")

    try:
        # Parse the expression into an AST
        # mode='eval' ensures only a single expression is processed
        tree = ast.parse(expr, mode='eval')
        return eval_node(tree.body)
    except (SyntaxError, KeyError, TypeError, ValueError, ZeroDivisionError) as e:
        raise e

@app.post("/calculator", response_model=CalculationResponse)
async def calculate(request: CalculationRequest):
    """
    Calculate the result of an arithmetic expression.
    """
    expression = request.expression
    
    # Resource exhaustion: bound the input length to prevent CPU-based DoS (e.g., deeply nested parentheses)
    if len(expression) > 1000:
        raise HTTPException(status_code=400, detail="Invalid input: Expression too long")

    try:
        # Use the safe_eval instead of eval() to eliminate RCE risks
        result = safe_eval(expression)
        
        # Ensure the result is a number and not something that could cause issues when converted to string
        if not isinstance(result, (int, float)):
            raise ValueError("Invalid result type")
            
        return CalculationResponse(result=str(result))
    except Exception:
        # Error handling: Catch all exceptions and return the documented 400 status code
        # without leaking internal stack traces or specific error messages.
        raise HTTPException(status_code=400, detail="Invalid input")

if __name__ == "__main__":
    # Start the webserver on port 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)