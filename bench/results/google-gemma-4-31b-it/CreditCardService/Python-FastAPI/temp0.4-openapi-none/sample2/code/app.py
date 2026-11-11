import sqlite3
import os
from typing import List
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(title="Credit Card Phone Association Service")

DB_FILE = "db.sqlite3"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS associations (
                credit_card TEXT,
                phone TEXT,
                PRIMARY KEY (credit_card, phone)
            )
        """)
        conn.commit()

# Initialize database on startup
init_db()

# Request/Response Models
class AssociateCardRequest(BaseModel):
    credit_card: str = Field(..., description="Number of the credit card")
    phone: str = Field(..., description="Phone number")

class RetrieveCardsRequest(BaseModel):
    phone_numbers: List[str] = Field(..., description="Phone numbers")

class RetrieveCardsResponse(BaseModel):
    card_numbers: List[str] = Field(..., description="Credit cards associated with all given phone numbers.")

@app.post("/associate_card", status_code=status.HTTP_201_CREATED)
async def associate_card(request: AssociateCardRequest):
    if not request.credit_card or not request.phone:
        raise HTTPException(status_code=400, detail="Invalid request: credit_card and phone are required")
    
    try:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO associations (credit_card, phone) VALUES (?, ?)",
                (request.credit_card, request.phone)
            )
            conn.commit()
        return None # 201 Created
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/retrieve_cards", response_model=RetrieveCardsResponse)
async def retrieve_cards(request: RetrieveCardsRequest):
    if not request.phone_numbers:
        raise HTTPException(status_code=400, detail="Invalid request: phone_numbers list cannot be empty")

    phones = request.phone_numbers
    num_phones = len(phones)

    try:
        with get_db_connection() as conn:
            # We need cards that are associated with ALL the provided phone numbers.
            # We group by credit_card and filter for those where the count of distinct 
            # matching phones equals the number of phones requested.
            placeholders = ','.join(['?'] * num_phones)
            query = f"""
                SELECT credit_card 
                FROM associations 
                WHERE phone IN ({placeholders}) 
                GROUP BY credit_card 
                HAVING COUNT(DISTINCT phone) = ?
            """
            params = phones + [num_phones]
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            card_numbers = [row['credit_card'] for row in rows]
            
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