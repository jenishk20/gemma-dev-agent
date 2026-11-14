import sqlite3
import os
from typing import List
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

# --- Configuration ---
DB_FILE = "db.sqlite3"

app = FastAPI(title="Credit Card Phone Association Service")

# --- Database Setup ---
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # We use a junction table to handle the many-to-many relationship 
        # between credit cards and phone numbers.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS associations (
                card_number TEXT,
                phone_number TEXT,
                PRIMARY KEY (card_number, phone_number)
            )
        """)
        conn.commit()

init_db()

# --- Schemas ---
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
    """
    Create a new association of a credit card number with a phone number.
    """
    if not request.credit_card or not request.phone:
        raise HTTPException(status_code=400, detail="Invalid request: credit_card and phone are required")

    try:
        with get_db_connection() as conn:
            # Use parameterized query to prevent SQL injection
            conn.execute(
                "INSERT OR IGNORE INTO associations (card_number, phone_number) VALUES (?, ?)",
                (request.credit_card, request.phone)
            )
            conn.commit()
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return None

@app.post("/retrieve_cards", response_model=RetrieveCardsResponse)
async def retrieve_cards(request: RetrieveCardsRequest):
    """
    Retrieve cards associated with a set of phone numbers. 
    A card must be associated with all given phone numbers to be returned.
    """
    if not request.phone_numbers:
        raise HTTPException(status_code=400, detail="phone_numbers list cannot be empty")

    try:
        with get_db_connection() as conn:
            # To find cards associated with ALL provided phone numbers:
            # 1. Filter for rows containing any of the target phones.
            # 2. Group by card_number.
            # 3. Having count of distinct phones equals the length of the input list.
            
            placeholders = ','.join(['?'] * len(request.phone_numbers))
            query = f"""
                SELECT card_number 
                FROM associations 
                WHERE phone_number IN ({placeholders})
                GROUP BY card_number 
                HAVING COUNT(DISTINCT phone_number) = ?
            """
            
            params = request.phone_numbers + [len(request.phone_numbers)]
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            cards = [row['card_number'] for row in rows]
            
            if not cards:
                # The schema specifies 404 for Not Found
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