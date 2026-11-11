import sqlite3
import os
from typing import List
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

# Database setup
DB_FILE = "db.sqlite3"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # Create table for associations
        # We use a unique constraint to prevent duplicate card-phone pairs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS associations (
                credit_card TEXT,
                phone TEXT,
                PRIMARY KEY (credit_card, phone)
            )
        ''')
        conn.commit()

# Pydantic Models
class AssociateCardRequest(BaseModel):
    credit_card: str = Field(..., description="Number of the credit card")
    phone: str = Field(..., description="Phone number")

class RetrieveCardsRequest(BaseModel):
    phone_numbers: List[str] = Field(..., description="Phone numbers")

class RetrieveCardsResponse(BaseModel):
    card_numbers: List[str] = Field(..., description="Credit cards associated with all given phone numbers.")

# FastAPI App
app = FastAPI(title="Credit Card Phone Association Service")

@app.on_event("startup")
async def startup_event():
    init_db()

@app.post("/associate_card", status_code=status.HTTP_201_CREATED)
async def associate_card(request: AssociateCardRequest):
    if not request.credit_card or not request.phone:
        raise HTTPException(status_code=400, detail="Invalid request: credit_card and phone are required")
    
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO associations (credit_card, phone) VALUES (?, ?)", 
                (request.credit_card, request.phone)
            )
            conn.commit()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return None

@app.post("/retrieve_cards", response_model=RetrieveCardsResponse)
async def retrieve_cards(request: RetrieveCardsRequest):
    if not request.phone_numbers:
        raise HTTPException(status_code=400, detail="Invalid request: phone_numbers list cannot be empty")
    
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            
            # To find cards associated with ALL given phone numbers, 
            # we filter for the phone numbers and group by card, 
            # then ensure the count of distinct phones matches the length of the input list.
            placeholders = ','.join(['?'] * len(request.phone_numbers))
            query = f'''
                SELECT credit_card 
                FROM associations 
                WHERE phone IN ({placeholders}) 
                GROUP BY credit_card 
                HAVING COUNT(DISTINCT phone) = ?
            '''
            
            params = request.phone_numbers + [len(request.phone_numbers)]
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            card_numbers = [row[0] for row in rows]
            
            if not card_numbers:
                raise HTTPException(status_code=404, detail="Not found")
                
            return RetrieveCardsResponse(card_numbers=card_numbers)
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)