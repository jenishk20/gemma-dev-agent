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
    card_numbers: List[str]

# --- Database Logic ---
DB_FILE = "db.sqlite3"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # Table to store the association between cards and phones
        # We use a composite primary key to avoid duplicate associations
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
            cursor.execute("INSERT INTO card_phone (credit_card, phone) VALUES (?, ?)", (card, phone))
            conn.commit()
    except sqlite3.IntegrityError:
        # Already exists, we can ignore or handle as success
        pass

def get_cards_for_phones(phones: List[str]) -> List[str]:
    if not phones:
        return []
    
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # To find cards associated with ALL given phone numbers:
        # 1. Filter for cards that have at least one of the phones
        # 2. Group by card and count how many of the requested phones it has
        # 3. If the count equals the number of requested phones, it's a match.
        
        placeholders = ','.join(['?'] * len(phones))
        query = f"""
            SELECT credit_card 
            FROM card_phone 
            WHERE phone IN ({placeholders}) 
            GROUP BY credit_card 
            HAVING COUNT(DISTINCT phone) = ?
        """
        # Pass the list of phones and the length of the list as the final parameter
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
    if not request.credit_card or not request.phone:
        raise HTTPException(status_code=400, detail="Invalid request: missing fields")
    
    add_association(request.credit_card, request.phone)
    return None

@app.post("/retrieve_cards", response_model=RetrieveCardsResponse)
async def retrieve_cards(request: RetrieveCardsRequest):
    if not request.phone_numbers:
        raise HTTPException(status_code=400, detail="Invalid request: phone_numbers list cannot be empty")
    
    cards = get_cards_for_phones(request.phone_numbers)
    
    if not cards:
        # The OpenAPI schema suggests 404 for Not Found
        raise HTTPException(status_code=404, detail="No cards found associated with all provided phone numbers")
        
    return RetrieveCardsResponse(card_numbers=cards)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)