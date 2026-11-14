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
    def validate_non_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v

class RetrieveCardsRequest(BaseModel):
    phone_numbers: List[str] = Field(..., description="Phone numbers")

    @validator('phone_numbers')
    def validate_phones(cls, v):
        if not v:
            raise ValueError("phone_numbers list cannot be empty")
        for phone in v:
            if not phone or not phone.strip():
                raise ValueError("Phone number cannot be empty")
        return v

class RetrieveCardsResponse(BaseModel):
    card_numbers: List[str] = Field(..., description="Credit cards associated with all given phone numbers.")

# --- Database Logic ---
# Hardcoded path to prevent path traversal/injection
DB_PATH = "db.sqlite3"

def init_db():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS card_phone_association (
                    credit_card TEXT,
                    phone TEXT,
                    PRIMARY KEY (credit_card, phone)
                )
            """)
            conn.commit()
    except Exception:
        # Internal error during init is critical, but we follow the rule of not leaking details
        pass

def add_association(credit_card: str, phone: str):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # Using parameterized query to prevent SQL Injection
            cursor.execute(
                "INSERT INTO card_phone_association (credit_card, phone) VALUES (?, ?)",
                (credit_card, phone)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        pass
    except Exception:
        raise RuntimeError("Database error")

def get_cards_for_phones(phones: List[str]) -> List[str]:
    # Resource exhaustion check: limit the number of phones processed in one request
    if len(phones) > 1000:
        raise RuntimeError("Too many phone numbers requested")

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # Use parameterized query for the IN clause
            # We generate a string of '?' and pass the list as parameters
            placeholders = ','.join(['?'] * len(phones))
            query = f"""
                SELECT credit_card 
                FROM card_phone_association 
                WHERE phone IN ({placeholders}) 
                GROUP BY credit_card 
                HAVING COUNT(DISTINCT phone) = ?
            """
            params = phones + [len(phones)]
            cursor.execute(query, params)
            results = cursor.fetchall()
            return [row[0] for row in results]
    except Exception:
        raise RuntimeError("Database error")

# --- App Initialization ---
app = FastAPI(title="Credit Card Phone Association Service")

# Global exception handler to prevent leaking stack traces (Internal Server Error)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # We return 400 for "Invalid Request" as per OpenAPI if it's a validation error, 
    # otherwise a generic 500 without leaking details.
    return HTTPException(status_code=500, detail="Internal server error")

@app.on_event("startup")
async def startup_event():
    init_db()

@app.post("/associate_card", status_code=status.HTTP_201_CREATED)
async def associate_card(request: AssociateCardRequest):
    try:
        add_association(request.credit_card, request.phone)
    except Exception:
        # Map internal errors to the 400 "Invalid request" as per schema for malformed/bad input
        raise HTTPException(status_code=400, detail="Invalid request")
    return None

@app.post("/retrieve_cards", response_model=RetrieveCardsResponse)
async def retrieve_cards(request: RetrieveCardsRequest):
    try:
        cards = get_cards_for_phones(request.phone_numbers)
        if not cards:
            raise HTTPException(status_code=404, detail="Not found")
        return RetrieveCardsResponse(card_numbers=cards)
    except HTTPException as he:
        raise he
    except Exception:
        # Map internal errors or resource exhaustion to 400 as per schema
        raise HTTPException(status_code=400, detail="Invalid request")

if __name__ == "__main__":
    import uvicorn
    # Port 5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)