import sqlite3
import os
from typing import List
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

# Configuration
DB_PATH = "db.sqlite3"

app = FastAPI(title="Credit Card Phone Association Service")

# --- Database Logic ---

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # Create table to store associations
        # We use a composite primary key to prevent duplicate associations
        conn.execute("""
            CREATE TABLE IF NOT EXISTS card_phone_association (
                credit_card TEXT NOT NULL,
                phone TEXT NOT NULL,
                PRIMARY KEY (credit_card, phone)
            )
        """)
        conn.commit()

# Initialize DB on startup
init_db()

# --- Pydantic Models ---

class AssociateCardRequest(BaseModel):
    credit_card: str = Field(..., description="Number of the credit card")
    phone: str = Field(..., description="Phone number")

class RetrieveCardsRequest(BaseModel):
    phone_numbers: List[str] = Field(..., description="Phone numbers")

class RetrieveCardsResponse(BaseModel):
    card_numbers: List[str] = Field(..., description="Credit cards associated with all given phone numbers.")

# --- Endpoints ---

@app.post("/associate_card", status_code=status.HTTP_201_CREATED)
async def associate_card(request: AssociateCardRequest):
    if not request.credit_card or not request.phone:
        raise HTTPException(status_code=400, detail="Invalid request: credit_card and phone are required")
    
    try:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO card_phone_association (credit_card, phone) VALUES (?, ?)",
                (request.credit_card, request.phone)
            )
            conn.commit()
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return None

@app.post("/retrieve_cards", response_model=RetrieveCardsResponse)
async def retrieve_cards(request: RetrieveCardsRequest):
    if not request.phone_numbers:
        raise HTTPException(status_code=400, detail="Invalid request: phone_numbers list cannot be empty")

    try:
        with get_db_connection() as conn:
            # To find cards associated with ALL provided phone numbers:
            # We filter for cards that have any of the target phones, 
            # group by card, and ensure the count of distinct phones matches the input list size.
            
            # Use a parameterized query to prevent SQL injection
            placeholders = ','.join(['?'] * len(request.phone_numbers))
            query = f"""
                SELECT credit_card 
                FROM card_phone_association 
                WHERE phone IN ({placeholders}) 
                GROUP BY credit_card 
                HAVING COUNT(DISTINCT phone) = ?
            """
            
            params = request.phone_numbers + [len(request.phone_numbers)]
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            cards = [row['credit_card'] for row in rows]
            
            if not cards:
                # The schema suggests 404 if not found, though 200 with empty list is more common.
                # Following the schema's explicit 404 response option.
                raise HTTPException(status_code=404, detail="No cards found associated with all provided phone numbers")
            
            return RetrieveCardsResponse(card_numbers=cards)
            
    except HTTPException:
        raise
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)