import sqlite3
import os
from typing import List
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

# Configuration
DB_FILE = "db.sqlite3"

app = FastAPI(title="Credit Card Phone Association Service")

# Pydantic Models for Request/Response validation
class AssociateCardRequest(BaseModel):
    credit_card: str = Field(..., description="Number of the credit card")
    phone: str = Field(..., description="Phone number")

class RetrieveCardsRequest(BaseModel):
    phone_numbers: List[str] = Field(..., description="Phone numbers")

class RetrieveCardsResponse(BaseModel):
    card_numbers: List[str] = Field(..., description="Credit cards associated with all given phone numbers.")

# Database initialization
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # Create table for associations
        # We use a composite primary key to avoid duplicate entries of the same card-phone pair
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS associations (
                credit_card TEXT NOT NULL,
                phone TEXT NOT NULL,
                PRIMARY KEY (credit_card, phone)
            )
        """)
        conn.commit()

@app.on_event("startup")
def startup_event():
    init_db()

@app.post("/associate_card", status_code=status.HTTP_201_CREATED)
async def associate_card(request: AssociateCardRequest):
    """
    Create a new association of a credit card number with a phone number.
    """
    if not request.credit_card or not request.phone:
        raise HTTPException(status_code=400, detail="Invalid request: credit_card and phone are required")

    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            # Use parameterized query to prevent SQL Injection
            cursor.execute(
                "INSERT OR IGNORE INTO associations (credit_card, phone) VALUES (?, ?)",
                (request.credit_card, request.phone)
            )
            conn.commit()
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    return None

@app.post("/retrieve_cards", response_model=RetrieveCardsResponse)
async def retrieve_cards(request: RetrieveCardsRequest):
    """
    Retrieve cards associated with a set of phone numbers. 
    A card must be associated with all given phone numbers to be returned.
    """
    phones = request.phone_numbers
    if not phones:
        raise HTTPException(status_code=400, detail="Phone numbers list cannot be empty")

    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            
            # To find cards associated with ALL provided phone numbers:
            # 1. Filter for cards that have any of the target phones.
            # 2. Group by card number.
            # 3. Filter for groups where the count of distinct phones equals the count of requested phones.
            
            placeholders = ','.join(['?'] * len(phones))
            query = f"""
                SELECT credit_card 
                FROM associations 
                WHERE phone IN ({placeholders}) 
                GROUP BY credit_card 
                HAVING COUNT(DISTINCT phone) = ?
            """
            
            # Parameters: the list of phones, then the total count of phones
            params = phones + [len(phones)]
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            card_numbers = [row[0] for row in rows]
            
            if not card_numbers:
                # The schema specifies 404 for Not Found
                raise HTTPException(status_code=404, detail="No cards found associated with all provided phone numbers")
            
            return RetrieveCardsResponse(card_numbers=card_numbers)

    except HTTPException:
        raise
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)