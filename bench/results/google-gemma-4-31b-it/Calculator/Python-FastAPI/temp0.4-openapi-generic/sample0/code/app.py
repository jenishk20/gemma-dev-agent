import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import ast
import operator

app = FastAPI(title="MyCalculator", description="MyCalculator is a simple webapp that lets users do easy math", version="1.0.11")

class CalculationRequest(BaseModel):
    expression: str = Field(..., example="1 + 2*3")

class CalculationResponse(BaseModel):
    result: str

def safe_eval(expr):
    """
    Safely evaluate a mathematical expression.
    Uses ast.parse to ensure only allowed operators and numbers are used,
    avoiding the security risks of the built-in eval().
    """
    # Allowed operators mapping
    operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }

    def eval_node(node):
        if isinstance(node, ast.Num):  # < Python 3.8
            return node.n
        elif isinstance(node, ast.Constant):  # >= Python 3.8
            if isinstance(node.value, (int, float)):
                return node.value
            raise TypeError(f"Unsupported constant type: {type(node.value)}")
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type in operators:
                left = eval_node(node.left)
                right = eval_node(node.right)
                return operators[op_type](left, right)
            raise TypeError(f"Unsupported operator: {op_type.__name__}")
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type in operators:
                operand = eval_node(node.operand)
                return operators[op_type](operand)
            raise TypeError(f"Unsupported unary operator: {op_type.__name__}")
        else:
            raise TypeError(f"Unsupported expression element: {type(node).__name__}")

    try:
        # Parse the expression into an AST
        tree = ast.parse(expr, mode='eval')
        result = eval_node(tree.body)
        return result
    except Exception as e:
        raise e

@app.post("/calculator", response_model=CalculationResponse)
async def calculate(request: CalculationRequest):
    try:
        # Evaluate the expression safely
        res = safe_eval(request.expression)
        # Convert result to string as per OpenAPI schema example
        return CalculationResponse(result=str(res))
    except (SyntaxError, TypeError, ZeroDivisionError, ValueError) as e:
        # Return 400 for invalid inputs or math errors (like division by zero)
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
    except Exception:
        # Generic 400 for any other parsing failure
        raise HTTPException(status_code=400, detail="Invalid input")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)