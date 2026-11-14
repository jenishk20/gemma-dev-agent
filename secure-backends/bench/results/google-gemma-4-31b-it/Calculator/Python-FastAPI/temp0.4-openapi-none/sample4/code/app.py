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
    
    # Security: We must be careful with eval(). 
    # We restrict the available globals and locals to prevent execution of arbitrary code.
    # We only allow basic math operations and digits.
    allowed_chars = set("0123456789+-*/(). ")
    if not all(char in allowed_chars for char in expression):
        raise HTTPException(status_code=400, detail="Invalid input: Only numbers and basic operators are allowed.")

    try:
        # eval is used here as a simple way to parse the math expression 
        # given the strict character whitelist above.
        result_val = eval(expression, {"__builtins__": {}}, {})
        return CalculationResponse(result=str(result_val))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid input: Expression could not be evaluated.")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)