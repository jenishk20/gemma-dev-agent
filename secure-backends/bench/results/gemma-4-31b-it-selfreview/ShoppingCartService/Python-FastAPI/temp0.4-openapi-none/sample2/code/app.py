import sqlite3
import uuid
import os
from typing import List
from fastapi import FastAPI, HTTPException, status, Request
from pydantic import BaseModel, Field

# --- Database Setup ---
DB_FILE = "db.sqlite3"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # Table for carts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS carts (
                cart_id TEXT PRIMARY KEY
            )
        """)
        # Table for items in carts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cart_items (
                cart_id TEXT,
                item_id INTEGER,
                count INTEGER,
                PRIMARY KEY (cart_id, item_id),
                FOREIGN KEY (cart_id) REFERENCES carts (cart_id)
            )
        """)
        conn.commit()

init_db()

# --- Pydantic Models ---
# Added constraints to prevent resource exhaustion (extremely large integers)
class CreateCartResponse(BaseModel):
    cart_id: str

class AddToCartRequest(BaseModel):
    cart_id: str = Field(..., max_length=36) # UUIDs are 36 chars
    item_id: int = Field(..., lt=2**63 - 1, gt=-(2**63))
    count: int = Field(..., lt=1000000, gt=-1000000) # Prevent overflow/extreme values

class RetrieveCartRequest(BaseModel):
    cart_id: str = Field(..., max_length=36)

class CartItem(BaseModel):
    item_id: int
    count: int

class RetrieveCartResponse(BaseModel):
    items: List[CartItem]

# --- FastAPI App ---
app = FastAPI(title="Shopping Cart Service")

# Global exception handler to prevent leaking internal stack traces
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log the error internally here if a logger was available
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
        detail="Internal server error"
    )

@app.post("/create_cart", response_model=CreateCartResponse, status_code=status.HTTP_201_CREATED)
async def create_cart():
    # Use cryptographically secure UUID
    cart_id = str(uuid.uuid4())
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            # Parameterized query prevents SQL injection
            cursor.execute("INSERT INTO carts (cart_id) VALUES (?)", (cart_id,))
            conn.commit()
    except sqlite3.Error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")
    return {"cart_id": cart_id}

@app.post("/add_to_cart", status_code=status.HTTP_200_OK)
async def add_to_cart(request: AddToCartRequest):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            
            # Parameterized query prevents SQL injection
            cursor.execute("SELECT 1 FROM carts WHERE cart_id = ?", (request.cart_id,))
            if cursor.fetchone() is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
            
            cursor.execute("SELECT count FROM cart_items WHERE cart_id = ? AND item_id = ?", 
                           (request.cart_id, request.item_id))
            row = cursor.fetchone()
            current_count = row[0] if row else 0
            
            new_count = current_count + request.count
            
            if new_count < 0:
                # As per schema: 400 for invalid request
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request: count cannot be negative")
            
            if new_count == 0:
                cursor.execute("DELETE FROM cart_items WHERE cart_id = ? AND item_id = ?", 
                               (request.cart_id, request.item_id))
            else:
                # Parameterized query prevents SQL injection
                cursor.execute("""
                    INSERT INTO cart_items (cart_id, item_id, count) 
                    VALUES (?, ?, ?) 
                    ON CONFLICT(cart_id, item_id) DO UPDATE SET count = excluded.count
                """, (request.cart_id, request.item_id, new_count))
            
            conn.commit()
    except sqlite3.Error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")
    return None

@app.post("/retrieve_cart", response_model=RetrieveCartResponse)
async def retrieve_cart(request: RetrieveCartRequest):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            
            # Parameterized query prevents SQL injection
            cursor.execute("SELECT 1 FROM carts WHERE cart_id = ?", (request.cart_id,))
            if cursor.fetchone() is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
            
            cursor.execute("SELECT item_id, count FROM cart_items WHERE cart_id = ?", (request.cart_id,))
            rows = cursor.fetchall()
            
            # Limit the number of items returned to prevent resource exhaustion (DoS)
            # While a cart usually has few items, we cap it at 10,000
            if len(rows) > 10000:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart too large")
                
            items = [CartItem(item_id=row[0], count=row[1]) for row in rows]
            return {"items": items}
    except sqlite3.Error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")

if __name__ == "__main__":
    import uvicorn
    # Port 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)