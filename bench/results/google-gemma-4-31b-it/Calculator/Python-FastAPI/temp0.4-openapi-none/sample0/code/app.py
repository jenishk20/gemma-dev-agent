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

    def eval_(node):
        if isinstance(node, ast.Num):  # < Python 3.8
            return node.n
        elif isinstance(node, ast.Constant):  # Python 3.8+
            return node.value
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type in operators:
                left = eval_(node.left)
                right = eval_(node.right)
                return operators[op_type](left, right)
            else:
                raise TypeError(f"Unsupported operator: {op_type}")
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type in operators:
                operand = eval_(node.operand)
                return operators[op_type](operand)
            else:
                raise TypeError(f"Unsupported operator: {op_type}")
        else:
            raise TypeError(f"Unsupported expression element: {type(node)}")

    try:
        # Parse the expression into an AST
        tree = ast.parse(expr, mode='eval')
        return eval_(tree.body)
    except Exception as e:
        raise e

@app.post("/calculator", response_model=CalculationResponse)
async def calculate(request: CalculationRequest):
    try:
        # Evaluate the expression safely
        res = safe_eval(request.expression)
        # Convert result to string as per OpenAPI schema example
        return CalculationResponse(result=str(res))
    except Exception:
        # Return 400 for invalid input/expressions
        raise HTTPException(status_code=400, detail="Invalid input")

if __name__ == "__main__":
    # Start the server on port 5000 and host 0.0.0.0
    uvicorn.run(app, host="0.0.0.0", port=5000)