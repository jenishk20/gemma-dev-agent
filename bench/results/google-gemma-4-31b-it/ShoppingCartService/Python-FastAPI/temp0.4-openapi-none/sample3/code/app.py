import sqlite3
import uuid
import os
from typing import List
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

# --- Database Setup ---
DB_FILE = "db.sqlite3"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # Table for carts
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS carts (cart_id TEXT PRIMARY KEY)"
        )
        # Table for cart items
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS cart_items ("
            "cart_id TEXT, "
            "item_id INTEGER, "
            "count INTEGER, "
            "PRIMARY KEY (cart_id, item_id), "
            "FOREIGN KEY (cart_id) REFERENCES carts(cart_id)"
            ")"
        )
        conn.commit()

init_db()

# --- Models ---
class CreateCartResponse(BaseModel):
    cart_id: str

class AddToCartRequest(BaseModel):
    cart_id: str
    item_id: int
    count: int

class CartItem(BaseModel):
    item_id: int
    count: int

class RetrieveCartResponse(BaseModel):
    items: List[CartItem]

class RetrieveCartRequest(BaseModel):
    cart_id: str

# --- App ---
app = FastAPI(title="Shopping Cart Service")

@app.post("/create_cart", response_model=CreateCartResponse, status_code=status.HTTP_201_CREATED)
async def create_cart():
    cart_id = str(uuid.uuid4())
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO carts (cart_id) VALUES (?)", (cart_id,))
        conn.commit()
    return {"cart_id": cart_id}

@app.post("/add_to_cart")
async def add_to_cart(request: AddToCartRequest):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        
        # Check if cart exists
        cursor.execute("SELECT 1 FROM carts WHERE cart_id = ?", (request.cart_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Cart not found")
        
        # Get current count
        cursor.execute(
            "SELECT count FROM cart_items WHERE cart_id = ? AND item_id = ?", 
            (request.cart_id, request.item_id)
        )
        row = cursor.fetchone()
        current_count = row[0] if row else 0
        
        new_count = current_count + request.count
        
        if new_count <= 0:
            # Remove item if count drops to 0 or below
            cursor.execute(
                "DELETE FROM cart_items WHERE cart_id = ? AND item_id = ?", 
                (request.cart_id, request.item_id)
            )
        else:
            # Update or Insert
            cursor.execute(
                "INSERT INTO cart_items (cart_id, item_id, count) VALUES (?, ?, ?) "
                "ON CONFLICT(cart_id, item_id) DO UPDATE SET count = excluded.count",
                (request.cart_id, request.item_id, new_count)
            )
        
        conn.commit()
    return {"message": "Item added or removed successfully"}

@app.post("/retrieve_cart", response_model=RetrieveCartResponse)
async def retrieve_cart(request: RetrieveCartRequest):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        
        # Check if cart exists
        cursor.execute("SELECT 1 FROM carts WHERE cart_id = ?", (request.cart_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Cart not found")
        
        cursor.execute(
            "SELECT item_id, count FROM cart_items WHERE cart_id = ?", 
            (request.cart_id,)
        )
        rows = cursor.fetchall()
        
        items = [CartItem(item_id=row[0], count=row[1]) for row in rows]
        return {"items": items}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)