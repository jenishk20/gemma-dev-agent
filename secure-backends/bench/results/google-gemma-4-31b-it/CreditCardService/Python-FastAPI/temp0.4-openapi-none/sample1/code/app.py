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
        # We use a composite primary key to avoid duplicate associations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS associations (
                credit_card TEXT,
                phone TEXT,
                PRIMARY KEY (credit_card, phone)
            )
        """)
        conn.commit()

def add_association(card: str, phone: str):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO associations (credit_card, phone) VALUES (?, ?)", (card, phone))
            conn.commit()
    except sqlite3.IntegrityError:
        # If the association already exists, we just ignore it
        pass

def get_cards_for_phones(phones: List[str]) -> List[str]:
    if not phones:
        return []
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # We need cards that are associated with ALL the provided phone numbers.
        # We group by card and count how many of the requested phones are associated with it.
        # If the count equals the number of requested phones, the card matches.
        placeholders = ','.join(['?'] * len(phones))
        query = f"""
            SELECT credit_card 
            FROM associations 
            WHERE phone IN ({placeholders}) 
            GROUP BY credit_card 
            HAVING COUNT(DISTINCT phone) = ?
        """
        params = phones + [len(set(phones))]
        cursor.execute(query, params)
        results = cursor.fetchall()
        return [row[0] for row in results]

# --- App Setup ---
app = FastAPI(title="Credit Card Phone Association Service")

@app.on_event("startup")
async def startup_event():
    init_db()

@app.post("/associate_card", status_code=status.HTTP_201_CREATED)
async def associate_card(request: AssociateCardRequest):
    if not request.credit_card or not request.phone:
        raise HTTPException(status_code=400, detail="Invalid request: card and phone are required")
    
    add_association(request.credit_card, request.phone)
    return None

@app.post("/retrieve_cards", response_model=RetrieveCardsResponse)
async def retrieve_cards(request: RetrieveCardsRequest):
    if not request.phone_numbers:
        raise HTTPException(status_code=400, detail="Invalid request: phone_numbers list cannot be empty")
    
    cards = get_cards_for_phones(request.phone_numbers)
    
    if not cards:
        # The schema specifies 404 for Not Found
        raise HTTPException(status_code=404, detail="No cards found associated with all provided phone numbers")
        
    return RetrieveCardsResponse(card_numbers=cards)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)