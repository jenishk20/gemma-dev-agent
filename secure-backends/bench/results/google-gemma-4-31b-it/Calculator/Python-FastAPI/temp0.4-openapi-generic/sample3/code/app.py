import uvicorn
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
import ast
import operator

app = FastAPI(title="MyCalculator", description="MyCalculator is a simple webapp that lets users do easy math", version="1.0.11")

# Pydantic models for request and response based on OpenAPI schema
class CalculationRequest(BaseModel):
    expression: str = Field(..., example="1 + 2*3")

class CalculationResponse(BaseModel):
    result: str

def safe_eval(expr):
    """
    Safely evaluate a mathematical expression.
    Uses ast.parse to ensure only allowed operations are performed,
    preventing arbitrary code execution (unlike eval()).
    """
    # Allowed operators mapping
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
            raise TypeError(f"Unsupported constant type: {type(node.value)}")
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type in operators:
                left = eval_node(node.left)
                right = eval_node(node.right)
                # Handle division by zero
                if op_type == ast.Div and right == 0:
                    raise ZeroDivisionError("Division by zero")
                return operators[op_type](left, right)
            raise TypeError(f"Unsupported operator: {op_type}")
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type in operators:
                operand = eval_node(node.operand)
                return operators[op_type](operand)
            raise TypeError(f"Unsupported unary operator: {op_type}")
        else:
            raise TypeError(f"Unsupported expression element: {type(node)}")

    try:
        # Parse the expression into an AST
        tree = ast.parse(expr, mode='eval')
        return eval_node(tree.body)
    except (SyntaxError, TypeError, ZeroDivisionError) as e:
        raise e
    except Exception:
        raise ValueError("Invalid expression")

@app.post("/calculator", response_model=CalculationResponse)
async def calculate(request: CalculationRequest):
    """
    Calculate the result of an arithmetic expression.
    """
    try:
        # We use a safe evaluator to prevent RCE vulnerabilities
        res = safe_eval(request.expression)
        # Convert result to string as per the OpenAPI schema example
        return CalculationResponse(result=str(res))
    except (SyntaxError, TypeError, ZeroDivisionError, ValueError) as e:
        # Return 400 for invalid inputs as per schema
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid input")

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)