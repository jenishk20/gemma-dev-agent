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
    Using ast.literal_eval is not enough for operators, 
    so we implement a recursive descent parser using AST nodes.
    """
    # Allowed operators
    operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.BitXor: operator.xor,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def eval_(node):
        if isinstance(node, ast.Num):  # < Python 3.8
            return node.n
        elif isinstance(node, ast.Constant):  # Python 3.8+
            if isinstance(node.value, (int, float)):
                return node.value
            raise TypeError(f"Unsupported constant type: {type(node.value)}")
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in operators:
                raise TypeError(f"Unsupported operator: {op_type.__name__}")
            left = eval_(node.left)
            right = eval_(node.right)
            return operators[op_type](left, right)
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in operators:
                raise TypeError(f"Unsupported operator: {op_type.__name__}")
            operand = eval_(node.operand)
            return operators[op_type](operand)
        else:
            raise TypeError(f"Unsupported AST node: {type(node).__name__}")

    try:
        # Parse the expression into an AST
        # mode='eval' ensures only a single expression is provided
        tree = ast.parse(expr, mode='eval')
        return eval_(tree.body)
    except Exception as e:
        raise e

@app.post("/calculator", response_model=CalculationResponse)
async def calculate(request: CalculationRequest):
    """
    Calculate the result of an arithmetic expression
    """
    try:
        # We use a custom AST walker instead of eval() to prevent Remote Code Execution (RCE)
        res = safe_eval(request.expression)
        # Convert result to string to match OpenAPI schema example "7"
        return CalculationResponse(result=str(res))
    except (SyntaxError, TypeError, ZeroDivisionError, ValueError) as e:
        # Return 400 for invalid inputs or math errors (like division by zero)
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
    except Exception:
        # General catch-all for unexpected errors to prevent leaking internal state
        raise HTTPException(status_code=400, detail="Invalid input")

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)