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

def safe_eval(expr: str):
    """
    Safely evaluate a mathematical expression.
    Uses ast.parse to ensure only allowed operators and numbers are used,
    preventing arbitrary code execution (RCE) that would occur with eval().
    """
    # Allowed operators mapping
    operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.Mod: operator.mod,
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
            left = eval_node(node.left)
            right = eval_node(node.right)
            op_type = type(node.op)
            if op_type not in operators:
                raise TypeError(f"Unsupported operator: {op_type}")
            
            # Handle division by zero
            if op_type == ast.Div and right == 0:
                raise ZeroDivisionError("Division by zero")
                
            return operators[op_type](left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = eval_node(node.operand)
            op_type = type(node.op)
            if op_type not in operators:
                raise TypeError(f"Unsupported operator: {op_type}")
            return operators[op_type](operand)
        else:
            raise TypeError(f"Unsupported expression element: {type(node)}")

    try:
        # Parse the expression into an AST
        tree = ast.parse(expr, mode='eval')
        result = eval_node(tree.body)
        # Convert result to string to match OpenAPI schema
        return str(result)
    except (SyntaxError, TypeError, ZeroDivisionError) as e:
        raise e
    except Exception:
        raise ValueError("Invalid expression")

@app.post("/calculator", response_model=CalculationResponse)
async def calculate(request: CalculationRequest):
    try:
        # Sanitize and evaluate the expression
        res_value = safe_eval(request.expression)
        return CalculationResponse(result=res_value)
    except ZeroDivisionError:
        raise HTTPException(status_code=400, detail="Division by zero")
    except (SyntaxError, TypeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid input")

if __name__ == "__main__":
    # Start the server on port 5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)