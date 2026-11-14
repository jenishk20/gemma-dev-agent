import sqlite3
import os
from typing import List
from fastapi import FastAPI, HTTPException, status, Request
from pydantic import BaseModel, Field, validator

# --- Models ---
class AssociateCardRequest(BaseModel):
    credit_card: str = Field(..., description="Number of the credit card")
    phone: str = Field(..., description="Phone number")

    @validator('credit_card', 'phone')
    def check_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v

class RetrieveCardsRequest(BaseModel):
    phone_numbers: List[str] = Field(..., description="Phone numbers")

    @validator('phone_numbers')
    def check_list_not_empty(cls, v):
        if not v:
            raise ValueError("phone_numbers list cannot be empty")
        return v

class RetrieveCardsResponse(BaseModel):
    card_numbers: List[str] = Field(..., description="Credit cards associated with all given phone numbers.")

# --- Database Logic ---
# Hardcoded path to prevent path traversal
DB_PATH = "db.sqlite3"

def init_db():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS associations (
                    credit_card TEXT,
                    phone TEXT,
                    PRIMARY KEY (credit_card, phone)
                )
            """)
            conn.commit()
    except Exception:
        # Internal error handling to prevent leak of stack trace
        pass

def add_association(card: str, phone: str):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # Use parameterized query to prevent SQL Injection
            cursor.execute("INSERT INTO associations (credit_card, phone) VALUES (?, ?)", (card, phone))
            conn.commit()
    except sqlite3.IntegrityError:
        pass
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")

def get_cards_for_phones(phones: List[str]) -> List[str]:
    # Resource exhaustion protection: limit the number of phone numbers processed
    if len(phones) > 1000:
        raise HTTPException(status_code=400, detail="Too many phone numbers provided")

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # Use parameterized query to prevent SQL Injection
            # We use a set to ensure distinct phones for the count logic
            unique_phones = list(set(phones))
            placeholders = ','.join(['?'] * len(unique_phones))
            query = f"""
                SELECT credit_card 
                FROM associations 
                WHERE phone IN ({placeholders}) 
                GROUP BY credit_card 
                HAVING COUNT(DISTINCT phone) = ?
            """
            params = unique_phones + [len(unique_phones)]
            cursor.execute(query, params)
            results = cursor.fetchall()
            return [row[0] for row in results]
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")

# --- App Setup ---
app = FastAPI(title="Credit Card Phone Association Service")

@app.on_event("startup")
async def startup_event():
    init_db()

@app.post("/associate_card", status_code=status.HTTP_201_CREATED)
async def associate_card(request: AssociateCardRequest):
    # Pydantic validation handles empty strings via validator
    add_association(request.credit_card, request.phone)
    return None

@app.post("/retrieve_cards", response_model=RetrieveCardsResponse)
async def retrieve_cards(request: RetrieveCardsRequest):
    # Pydantic validation handles empty list via validator
    cards = get_cards_for_phones(request.phone_numbers)
    
    if not cards:
        # The schema specifies 404 for Not Found
        raise HTTPException(status_code=404, detail="No cards found associated with all provided phone numbers")
        
    return RetrieveCardsResponse(card_numbers=cards)

# Global exception handler to prevent leaking internal stack traces
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return HTTPException(status_code=500, detail="Internal Server Error")(status_code=500, detail="Internal Server Error")

if __name__ == "__main__":
    import uvicorn
    # Run on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)