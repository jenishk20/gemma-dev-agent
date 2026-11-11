import sqlite3
import os
from typing import List
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

# --- Models ---
class AssociateCardRequest(BaseModel):
    credit_card: str = Field(..., description="Number of the credit card")
    phone: str = Field(..., description="Phone number")

class RetrieveCardsRequest(BaseModel):
    phone_numbers: List[str] = Field(..., description="Phone numbers")

class RetrieveCardsResponse(BaseModel):
    card_numbers: List[str] = Field(..., description="Credit cards associated with all given phone numbers.")

# --- Database Logic ---
DB_PATH = "db.sqlite3"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Table to store the association between cards and phones
        # We use a unique constraint to prevent duplicate associations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS card_phone_association (
                credit_card TEXT,
                phone TEXT,
                PRIMARY KEY (credit_card, phone)
            )
        """)
        conn.commit()

def add_association(credit_card: str, phone: str):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO card_phone_association (credit_card, phone) VALUES (?, ?)",
                (credit_card, phone)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        # If the association already exists, we treat it as success (idempotent)
        pass

def get_cards_for_phones(phones: List[str]) -> List[str]:
    if not phones:
        return []
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # To find cards associated with ALL given phone numbers:
        # 1. Filter for rows containing any of the target phones
        # 2. Group by card
        # 3. Filter groups where the count of distinct phones matches the length of the input list
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

# --- App Initialization ---
app = FastAPI(title="Credit Card Phone Association Service")

@app.on_event("startup")
async def startup_event():
    init_db()

@app.post("/associate_card", status_code=status.HTTP_201_CREATED)
async def associate_card(request: AssociateCardRequest):
    if not request.credit_card or not request.phone:
        raise HTTPException(status_code=400, detail="Invalid request: credit_card and phone are required")
    
    add_association(request.credit_card, request.phone)
    return None

@app.post("/retrieve_cards", response_model=RetrieveCardsResponse)
async def retrieve_cards(request: RetrieveCardsRequest):
    if not request.phone_numbers:
        raise HTTPException(status_code=400, detail="Invalid request: phone_numbers list cannot be empty")
    
    cards = get_cards_for_phones(request.phone_numbers)
    
    if not cards:
        raise HTTPException(status_code=404, detail="Not found")
        
    return RetrieveCardsResponse(card_numbers=cards)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)