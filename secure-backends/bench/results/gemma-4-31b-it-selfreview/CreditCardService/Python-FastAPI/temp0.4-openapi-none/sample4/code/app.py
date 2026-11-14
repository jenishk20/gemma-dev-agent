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
            raise ValueError("Field cannot be empty or whitespace")
        return v.strip()

class RetrieveCardsRequest(BaseModel):
    phone_numbers: List[str] = Field(..., description="Phone numbers")

    @validator('phone_numbers')
    def validate_phones(cls, v):
        if not v:
            raise ValueError("phone_numbers list cannot be empty")
        for phone in v:
            if not phone or not phone.strip():
                raise ValueError("Phone number cannot be empty or whitespace")
        return [p.strip() for p in v]

class RetrieveCardsResponse(BaseModel):
    card_numbers: List[str]

# --- Database Logic ---
DB_FILE = "db.sqlite3"

def init_db():
    # Ensure DB_FILE is handled as a constant and not derived from user input
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS card_phone (
                credit_card TEXT,
                phone TEXT,
                PRIMARY KEY (credit_card, phone)
            )
        """)
        conn.commit()

def add_association(card: str, phone: str):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            # Use parameterized queries to prevent SQL Injection
            cursor.execute("INSERT INTO card_phone (credit_card, phone) VALUES (?, ?)", (card, phone))
            conn.commit()
    except sqlite3.IntegrityError:
        pass

def get_cards_for_phones(phones: List[str]) -> List[str]:
    # Resource exhaustion protection: limit the number of phones processed in one request
    if len(phones) > 100:
        raise HTTPException(status_code=400, detail="Too many phone numbers requested")
    
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # Parameterized query to prevent SQL Injection
        # We use a fixed number of placeholders based on the input list length
        placeholders = ','.join(['?'] * len(phones))
        query = f"""
            SELECT credit_card 
            FROM card_phone 
            WHERE phone IN ({placeholders}) 
            GROUP BY credit_card 
            HAVING COUNT(DISTINCT phone) = ?
        """
        cursor.execute(query, (*phones, len(phones)))
        results = cursor.fetchall()
        return [row[0] for row in results]

# --- App Initialization ---
app = FastAPI(title="Credit Card Phone Association Service")

@app.on_event("startup")
def startup_event():
    init_db()

@app.post("/associate_card", status_code=status.HTTP_201_CREATED)
async def associate_card(request: AssociateCardRequest):
    try:
        add_association(request.credit_card, request.phone)
        return None
    except Exception:
        # Generic error handling to prevent leaking internal database details/stack traces
        raise HTTPException(status_code=400, detail="Invalid request")

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
        # Generic error handling to prevent leaking internal details
        raise HTTPException(status_code=400, detail="Invalid request")

# Middleware to bound request size to prevent resource exhaustion (DoS)
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    # Limit request body to 1MB
    MAX_SIZE = 1024 * 1024 
    content_length = request.headers.get('content-length')
    if content_length and int(content_length) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="Request entity too large")
    return await call_next(request)

if __name__ == "__main__":
    import uvicorn
    # Port 5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)