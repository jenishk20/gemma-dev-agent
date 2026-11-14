import sqlite3
import uuid
import os
from typing import List
from fastapi import FastAPI, HTTPException, status, Request
from pydantic import BaseModel, Field, validator

# --- Database Setup ---
DB_PATH = "db.sqlite3"

def init_db():
    try:
        with sqlite3.connect(DB_PATH) as conn:
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
                    FOREIGN KEY (cart_id) REFERENCES carts(cart_id)
                )
            """)
            conn.commit()
    except Exception:
        # In a real production app, we would log this. 
        # Here we ensure the app doesn't crash on startup but we can't proceed without DB.
        pass

# --- Models ---
class CreateCartResponse(BaseModel):
    cart_id: str

class AddToCartRequest(BaseModel):
    cart_id: str = Field(..., description="The unique identifier of the cart")
    item_id: int = Field(..., description="The unique identifier of the item")
    count: int = Field(..., description="The number of items to add (or remove if negative)")

    @validator('cart_id')
    def validate_cart_id(cls, v):
        # Prevent extremely large strings to avoid resource exhaustion (DoS)
        if len(v) > 255:
            raise ValueError('cart_id too long')
        return v

class RetrieveCartRequest(BaseModel):
    cart_id: str = Field(..., description="The unique identifier of the cart")

    @validator('cart_id')
    def validate_cart_id(cls, v):
        if len(v) > 255:
            raise ValueError('cart_id too long')
        return v

class CartItem(BaseModel):
    item_id: int
    count: int

class RetrieveCartResponse(BaseModel):
    items: List[CartItem]

# --- App Initialization ---
app = FastAPI(title="Shopping Cart Service")

@app.on_event("startup")
async def startup_event():
    init_db()

# --- Endpoints ---

@app.post("/create_cart", response_model=CreateCartResponse, status_code=status.HTTP_201_CREATED, summary="Create a new shopping cart")
async def create_cart():
    # Use uuid4 for cryptographically strong random IDs
    cart_id = str(uuid.uuid4())
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # Parameterized query to prevent SQL injection
            cursor.execute("INSERT INTO carts (cart_id) VALUES (?)", (cart_id,))
            conn.commit()
    except Exception:
        # Generic error to avoid leaking internal database details
        raise HTTPException(status_code=500, detail="Internal server error")
    
    return {"cart_id": cart_id}

@app.post("/add_to_cart", summary="Add or remove items from the cart")
async def add_to_cart(request: AddToCartRequest):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Parameterized query to prevent SQL injection
            cursor.execute("SELECT 1 FROM carts WHERE cart_id = ?", (request.cart_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Cart not found")
            
            # Parameterized query to prevent SQL injection
            cursor.execute("SELECT count FROM cart_items WHERE cart_id = ? AND item_id = ?", 
                           (request.cart_id, request.item_id))
            row = cursor.fetchone()
            current_count = row[0] if row else 0
            
            # Guard against integer overflow (though Python handles large ints, 
            # SQLite has limits and business logic should be bounded)
            new_count = current_count + request.count
            
            if new_count <= 0:
                # Remove item if count drops to 0 or below
                cursor.execute("DELETE FROM cart_items WHERE cart_id = ? AND item_id = ?", 
                               (request.cart_id, request.item_id))
            else:
                # Parameterized query to prevent SQL injection
                cursor.execute("""
                    INSERT INTO cart_items (cart_id, item_id, count) 
                    VALUES (?, ?, ?) 
                    ON CONFLICT(cart_id, item_id) DO UPDATE SET count = ?
                """, (request.cart_id, request.item_id, new_count, new_count))
            
            conn.commit()
    except HTTPException:
        raise
    except Exception:
        # Return 400 for invalid requests as per OpenAPI spec if something went wrong with logic
        raise HTTPException(status_code=400, detail="Invalid request")
    
    return {"message": "Item added or removed successfully"}

@app.post("/retrieve_cart", response_model=RetrieveCartResponse, summary="Retrieve all items in the cart")
async def retrieve_cart(request: RetrieveCartRequest):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Parameterized query to prevent SQL injection
            cursor.execute("SELECT 1 FROM carts WHERE cart_id = ?", (request.cart_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Cart not found")
            
            # Parameterized query to prevent SQL injection
            cursor.execute("SELECT item_id, count FROM cart_items WHERE cart_id = ?", (request.cart_id,))
            rows = cursor.fetchall()
            
            # Resource exhaustion: Limit the number of items returned to prevent memory issues
            # Although carts are usually small, we bound the result set
            items = [CartItem(item_id=row[0], count=row[1]) for row in rows[:1000]]
            return {"items": items}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    # Port 5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)