import sqlite3
import os
from typing import List
from fastapi import FastAPI, HTTPException, status, Request
from pydantic import BaseModel, Field, field_validator

app = FastAPI(title="Credit Card Phone Association Service")

DB_FILE = "db.sqlite3"

# Resource exhaustion: Limit the number of phone numbers a user can query at once
# to prevent CPU/Memory exhaustion during the GROUP BY/HAVING operation.
MAX_PHONE_NUMBERS = 100

def get_db_connection():
    # Using a fixed filename prevents path traversal.
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        with get_db_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS associations (
                    credit_card TEXT,
                    phone TEXT,
                    PRIMARY KEY (credit_card, phone)
                )
            """)
            conn.commit()
    except Exception:
        # Internal failure during init is critical, but we avoid leaking details
        pass

# Initialize database on startup
init_db()

# Request/Response Models
class AssociateCardRequest(BaseModel):
    credit_card: str = Field(..., description="Number of the credit card")
    phone: str = Field(..., description="Phone number")

    @field_validator('credit_card', 'phone')
    @classmethod
    def validate_non_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v

class RetrieveCardsRequest(BaseModel):
    phone_numbers: List[str] = Field(..., description="Phone numbers")

    @field_validator('phone_numbers')
    @classmethod
    def validate_phones(cls, v):
        if not v:
            raise ValueError("phone_numbers list cannot be empty")
        if len(v) > MAX_PHONE_NUMBERS:
            raise ValueError(f"Too many phone numbers. Maximum allowed is {MAX_PHONE_NUMBERS}")
        for phone in v:
            if not phone or not phone.strip():
                raise ValueError("Phone numbers cannot be empty strings")
        return v

class RetrieveCardsResponse(BaseModel):
    card_numbers: List[str] = Field(..., description="Credit cards associated with all given phone numbers.")

@app.post("/associate_card", status_code=status.HTTP_201_CREATED)
async def associate_card(request: AssociateCardRequest):
    try:
        with get_db_connection() as conn:
            # Use parameterized query to prevent SQL Injection
            conn.execute(
                "INSERT OR IGNORE INTO associations (credit_card, phone) VALUES (?, ?)",
                (request.credit_card, request.phone)
            )
            conn.commit()
        return None 
    except Exception:
        # Catch-all to prevent leaking internal database stack traces
        raise HTTPException(status_code=400, detail="Invalid request")

@app.post("/retrieve_cards", response_model=RetrieveCardsResponse)
async def retrieve_cards(request: RetrieveCardsRequest):
    phones = request.phone_numbers
    num_phones = len(phones)

    try:
        with get_db_connection() as conn:
            # Use parameterized query to prevent SQL Injection.
            # The number of placeholders is derived from the length of the list, 
            # which is bounded by MAX_PHONE_NUMBERS to prevent resource exhaustion.
            placeholders = ','.join(['?'] * num_phones)
            query = f"""
                SELECT credit_card 
                FROM associations 
                WHERE phone IN ({placeholders}) 
                GROUP BY credit_card 
                HAVING COUNT(DISTINCT phone) = ?
            """
            params = phones + [num_phones]
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            card_numbers = [row['credit_card'] for row in rows]
            
            if not card_numbers:
                raise HTTPException(status_code=404, detail="Not found")
                
            return RetrieveCardsResponse(card_numbers=card_numbers)
    except HTTPException as he:
        raise he
    except Exception:
        # Catch-all to prevent leaking internal database stack traces
        raise HTTPException(status_code=400, detail="Invalid request")

if __name__ == "__main__":
    import uvicorn
    # Port 5000 as requested.
    uvicorn.run(app, host="0.0.0.0", port=5000)