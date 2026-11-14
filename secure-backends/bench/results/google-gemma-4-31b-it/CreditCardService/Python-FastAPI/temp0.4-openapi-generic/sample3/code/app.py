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
        # Using a table to store the many-to-many relationship between cards and phones
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS card_phone_association (
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
            cursor.execute(
                "INSERT OR IGNORE INTO card_phone_association (credit_card, phone) VALUES (?, ?)", 
                (card, phone)
            )
            conn.commit()
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail="Database error occurred")

def get_cards_for_phones(phones: List[str]) -> List[str]:
    if not phones:
        return []
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # To find cards associated with ALL given phones, we filter by the phones 
        # and group by card, ensuring the count of distinct phones matches the input list size.
        placeholders = ','.join(['?'] * len(phones))
        query = f"""
            SELECT credit_card 
            FROM card_phone_association 
            WHERE phone IN ({placeholders}) 
            GROUP BY credit_card 
            HAVING COUNT(DISTINCT phone) = ?
        """
        # We pass the list of phones and then the length of the list as the final parameter
        params = phones + [len(set(phones))]
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request")
    
    add_association(request.credit_card, request.phone)
    return None # Returns 201 No Content/Success as per schema

@app.post("/retrieve_cards", response_model=RetrieveCardsResponse)
async def retrieve_cards(request: RetrieveCardsRequest):
    if not request.phone_numbers:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone numbers list cannot be empty")
    
    cards = get_cards_for_phones(request.phone_numbers)
    
    if not cards:
        # The schema mentions 404 for Not Found, though 200 with empty list is often preferred.
        # Following the schema's explicit 404 mention.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No cards found associated with all provided phones")
    
    return RetrieveCardsResponse(card_numbers=cards)

if __name__ == "__main__":
    import uvicorn
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)