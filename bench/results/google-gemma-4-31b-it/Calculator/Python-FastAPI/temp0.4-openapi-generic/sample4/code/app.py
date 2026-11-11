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

# Define supported operators for safe evaluation
# We use a whitelist approach to avoid using eval() directly on untrusted input
OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}

def safe_eval(expr):
    """
    Safely evaluate a mathematical expression using Abstract Syntax Trees (AST).
    This prevents arbitrary code execution vulnerabilities associated with eval().
    """
    node = ast.parse(expr, mode='eval').body
    
    def eval_node(node):
        if isinstance(node, ast.Num):  # < Python 3.8
            return node.n
        elif isinstance(node, ast.Constant):  # Python 3.8+
            if isinstance(node.value, (int, float)):
                return node.value
            raise TypeError(f"Unsupported constant type: {type(node.value)}")
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in OPERATORS:
                raise TypeError(f"Unsupported operator: {op_type}")
            return OPERATORS[op_type](eval_node(node.left), eval_node(node.right))
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in OPERATORS:
                raise TypeError(f"Unsupported operator: {op_type}")
            return OPERATORS[op_type](eval_node(node.operand))
        else:
            raise TypeError(f"Unsupported expression element: {type(node)}")

    return eval_node(node)

@app.post("/calculator", response_model=CalculationResponse)
async def calculate(request: CalculationRequest):
    try:
        # We use a custom safe_eval instead of eval() to prevent RCE (Remote Code Execution)
        result = safe_eval(request.expression)
        # Convert result to string as per the OpenAPI schema example
        return CalculationResponse(result=str(result))
    except (SyntaxError, TypeError, ZeroDivisionError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid input")

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)