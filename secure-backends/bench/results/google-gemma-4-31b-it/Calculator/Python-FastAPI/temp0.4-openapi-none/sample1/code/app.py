import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="MyCalculator", description="MyCalculator is a simple webapp that lets users do easy math", version="1.0.11")

class CalculationRequest(BaseModel):
    expression: str

class CalculationResponse(BaseModel):
    result: str

@app.post("/calculator", response_model=CalculationResponse)
async def calculate(request: CalculationRequest):
    """
    Calculate the result of an arithmetic expression.
    """
    expression = request.expression
    
    # To prevent security vulnerabilities associated with eval(), 
    # we restrict the allowed characters to numbers, basic operators, and whitespace.
    allowed_chars = set("0123456789+-*/.() ")
    if not all(char in allowed_chars for char in expression):
        raise HTTPException(status_code=400, detail="Invalid input: Only numbers and basic arithmetic operators are allowed.")

    try:
        # eval is used here for simplicity given the constraints, 
        # but we have implemented a character whitelist above to mitigate risk.
        # We use a limited global/local scope to prevent access to built-in functions.
        res = eval(expression, {"__builtins__": {}}, {})
        return CalculationResponse(result=str(res))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid input: The expression could not be evaluated.")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)