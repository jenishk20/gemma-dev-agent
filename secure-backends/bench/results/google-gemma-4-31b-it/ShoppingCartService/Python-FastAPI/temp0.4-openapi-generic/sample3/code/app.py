import sqlite3
import uuid
import os
from typing import List, Dict
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

# --- Models ---

class CartCreateResponse(BaseModel):
    cart_id: str

class AddToCartRequest(BaseModel):
    cart_id: str
    item_id: int
    count: int

class RetrieveCartRequest(BaseModel):
    cart_id: str

class CartItem(BaseModel):
    item_id: int
    count: int

class RetrieveCartResponse(BaseModel):
    items: List[CartItem]

# --- Database Logic ---

DB_PATH = "db.sqlite3"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # Create carts table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS carts (
                cart_id TEXT PRIMARY KEY
            )
        """)
        # Create cart_items table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cart_items (
                cart_id TEXT,
                item_id INTEGER,
                count INTEGER,
                PRIMARY KEY (cart_id, item_id),
                FOREIGN KEY (cart_id) REFERENCES carts (cart_id)
            )
        """)
        conn.commit()

# --- App Initialization ---

app = FastAPI(title="Shopping Cart Service")

@app.on_event("startup")
async def startup_event():
    init_db()

# --- API Endpoints ---

@app.post("/create_cart", response_model=CartCreateResponse, status_code=status.HTTP_201_CREATED, summary="Create a new shopping cart")
async def create_cart():
    cart_id = str(uuid.uuid4())
    try:
        with get_db_connection() as conn:
            conn.execute("INSERT INTO carts (cart_id) VALUES (?)", (cart_id,))
            conn.commit()
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="Database error occurred")
    
    return CartCreateResponse(cart_id=cart_id)

@app.post("/add_to_cart", status_code=status.HTTP_200_OK, summary="Add or remove items from the cart")
async def add_to_cart(request: AddToCartRequest):
    with get_db_connection() as conn:
        # Verify cart exists
        cursor = conn.execute("SELECT 1 FROM carts WHERE cart_id = ?", (request.cart_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

        # Get current count
        cursor = conn.execute("SELECT count FROM cart_items WHERE cart_id = ? AND item_id = ?", 
                             (request.cart_id, request.item_id))
        row = cursor.fetchone()
        
        current_count = row['count'] if row else 0
        new_count = current_count + request.count

        if new_count < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Item count cannot be negative")

        if new_count == 0:
            conn.execute("DELETE FROM cart_items WHERE cart_id = ? AND item_id = ?", 
                         (request.cart_id, request.item_id))
        else:
            conn.execute("""
                INSERT INTO cart_items (cart_id, item_id, count) 
                VALUES (?, ?, ?) 
                ON CONFLICT(cart_id, item_id) DO UPDATE SET count = excluded.count
            """, (request.cart_id, request.item_id, new_count))
        
        conn.commit()
    return None

@app.post("/retrieve_cart", response_model=RetrieveCartResponse, summary="Retrieve all items in the cart")
async def retrieve_cart(request: RetrieveCartRequest):
    with get_db_connection() as conn:
        # Verify cart exists
        cursor = conn.execute("SELECT 1 FROM carts WHERE cart_id = ?", (request.cart_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

        cursor = conn.execute("SELECT item_id, count FROM cart_items WHERE cart_id = ?", (request.cart_id,))
        rows = cursor.fetchall()
        
        items = [CartItem(item_id=row['item_id'], count=row['count']) for row in rows]
        return RetrieveCartResponse(items=items)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)