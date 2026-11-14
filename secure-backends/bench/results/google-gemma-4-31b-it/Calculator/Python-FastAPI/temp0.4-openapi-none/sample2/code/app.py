import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Define the request and response models based on the OpenAPI schema
class CalculationRequest(BaseModel):
    expression: str

class CalculationResponse(BaseModel):
    result: str

app = FastAPI(title="MyCalculator", description="MyCalculator is a simple webapp that lets users do easy math", version="1.0.11")

@app.post("/calculator", response_model=CalculationResponse)
async def calculate(request: CalculationRequest):
    """
    Calculate the result of an arithmetic expression.
    """
    expression = request.expression
    
    # To prevent arbitrary code execution, we restrict the characters allowed in the expression.
    # Only digits, basic operators, parentheses, and whitespace are permitted.
    allowed_chars = set("0123456789+-*/(). ")
    if not all(char in allowed_chars for char in expression):
        raise HTTPException(status_code=400, detail="Invalid input: Only basic arithmetic characters are allowed.")

    try:
        # eval() is used here on a strictly filtered string to perform the calculation.
        # In a production environment, a proper parser (like ast.literal_eval or a custom lexer) is preferred.
        result = eval(expression, {"__builtins__": None}, {})
        return CalculationResponse(result=str(result))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid input: The expression could not be evaluated.")

if __name__ == "__main__":
    # Start the webserver on port 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)