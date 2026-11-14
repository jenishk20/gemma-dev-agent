import sqlite3
import os
from typing import List
from fastapi import FastAPI, HTTPException, status, Request
from pydantic import BaseModel, Field

# Database setup
DB_FILE = "db.sqlite3"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # Create table for associations
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
    # Input validation: ensure fields are not empty or just whitespace
    if not request.credit_card.strip() or not request.phone.strip():
        raise HTTPException(status_code=400, detail="Invalid request")
    
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            # Using parameterized query to prevent SQL Injection
            cursor.execute(
                "INSERT OR IGNORE INTO associations (credit_card, phone) VALUES (?, ?)", 
                (request.credit_card, request.phone)
            )
            conn.commit()
    except Exception:
        # Generic error to avoid leaking internal database details
        raise HTTPException(status_code=400, detail="Invalid request")
    
    return None

@app.post("/retrieve_cards", response_model=RetrieveCardsResponse)
async def retrieve_cards(request: RetrieveCardsRequest):
    # Resource exhaustion protection: limit the number of phone numbers processed in one request
    if not request.phone_numbers:
        raise HTTPException(status_code=400, detail="Invalid request")
    
    if len(request.phone_numbers) > 100:
        raise HTTPException(status_code=400, detail="Invalid request")

    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            
            # To find cards associated with ALL given phone numbers:
            # 1. Filter for the specific phone numbers.
            # 2. Group by credit card.
            # 3. Ensure the count of distinct phones matches the length of the input list.
            
            # Use parameterized placeholders for the IN clause to prevent SQL Injection
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
            
    except HTTPException as he:
        raise he
    except Exception:
        # Generic error to avoid leaking internal database details
        raise HTTPException(status_code=400, detail="Invalid request")

if __name__ == "__main__":
    import uvicorn
    # Port 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)