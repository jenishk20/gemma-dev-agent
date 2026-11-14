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
    try:
        # We use a restricted set of globals and locals for eval to mitigate security risks,
        # although in a production environment, a proper parser (like ast.literal_eval or a custom lexer) 
        # is recommended.
        allowed_chars = set("0123456789+-*/(). ")
        if not all(char in allowed_chars for char in request.expression):
            raise ValueError("Invalid characters in expression")
            
        # eval is used here to handle the arithmetic expression as per the schema example "1 + 2*3"
        result = eval(request.expression, {"__builtins__": None}, {})
        return CalculationResponse(result=str(result))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid input")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)