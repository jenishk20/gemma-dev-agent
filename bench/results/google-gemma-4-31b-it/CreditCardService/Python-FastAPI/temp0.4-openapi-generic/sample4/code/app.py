import sqlite3
import os
from typing import List
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

# --- Configuration & Models ---

app = FastAPI(title="Credit Card Phone Association Service")

class AssociateCardRequest(BaseModel):
    credit_card: str = Field(..., description="Number of the credit card")
    phone: str = Field(..., description="Phone number")

class RetrieveCardsRequest(BaseModel):
    phone_numbers: List[str] = Field(..., description="Phone numbers")

class RetrieveCardsResponse(BaseModel):
    card_numbers: List[str] = Field(..., description="Credit cards associated with all given phone numbers.")

DB_PATH = "db.sqlite3"

# --- Database Logic ---

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # Table to store the association between cards and phones
        # Using a composite primary key to prevent duplicate associations
        conn.execute("""
            CREATE TABLE IF NOT EXISTS associations (
                credit_card TEXT NOT NULL,
                phone TEXT NOT NULL,
                PRIMARY KEY (credit_card, phone)
            )
        """)
        conn.commit()

# Initialize database on startup
init_db()

# --- API Endpoints ---

@app.post("/associate_card", status_code=status.HTTP_201_CREATED)
async def associate_card(request: AssociateCardRequest):
    """
    Create a new association of a credit card number with a phone number.
    """
    if not request.credit_card or not request.phone:
        raise HTTPException(status_code=400, detail="Invalid request: card and phone are required")

    try:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO associations (credit_card, phone) VALUES (?, ?)",
                (request.credit_card, request.phone)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        # If the association already exists, we can treat it as success or ignore
        pass
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Database error: {str(e)}")

    return None

@app.post("/retrieve_cards", response_model=RetrieveCardsResponse)
async def retrieve_cards(request: RetrieveCardsRequest):
    """
    Retrieve cards associated with a set of phone numbers. 
    A card must be associated with all given phone numbers to be returned.
    """
    phones = request.phone_numbers
    if not phones:
        # If no phone numbers are provided, the logic of "associated with all" 
        # is ambiguous. Based on typical API behavior, we return an empty list or 400.
        return RetrieveCardsResponse(card_numbers=[])

    try:
        with get_db_connection() as conn:
            # We need cards that appear in the associations table for EVERY phone in the list.
            # We group by credit_card and filter for those where the count of distinct 
            # phones matching the input list equals the size of the input list.
            
            # Use a parameterized query to prevent SQL injection
            placeholders = ','.join(['?'] * len(phones))
            query = f"""
                SELECT credit_card 
                FROM associations 
                WHERE phone IN ({placeholders}) 
                GROUP BY credit_card 
                HAVING COUNT(DISTINCT phone) = ?
            """
            
            params = phones + [len(set(phones))]
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            cards = [row['credit_card'] for row in rows]
            
            if not cards:
                # The schema allows 404, but usually, an empty list is returned for 200.
                # However, to strictly follow the schema's response options:
                # If no cards are found, we return 200 with empty list or 404.
                # We'll return 200 with empty list as it's standard for search.
                return RetrieveCardsResponse(card_numbers=[])
            
            return RetrieveCardsResponse(card_numbers=cards)

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request or server error: {str(e)}")

# --- Server Entry Point ---

if __name__ == "__main__":
    import uvicorn
    # Run on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)