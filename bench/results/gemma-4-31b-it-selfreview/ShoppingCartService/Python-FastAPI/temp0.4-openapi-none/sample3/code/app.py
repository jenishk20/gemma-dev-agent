import sqlite3
import uuid
import os
from typing import List
from fastapi import FastAPI, HTTPException, status, Request
from pydantic import BaseModel, Field

# --- Database Setup ---
DB_FILE = "db.sqlite3"

def init_db():
    # Using a context manager for the connection
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
# Added constraints to prevent resource exhaustion (e.g., extremely large integers)
class CreateCartResponse(BaseModel):
    cart_id: str

class AddToCartRequest(BaseModel):
    cart_id: str = Field(..., max_length=100)
    item_id: int = Field(...)
    count: int = Field(...)

class CartItem(BaseModel):
    item_id: int
    count: int

class RetrieveCartResponse(BaseModel):
    items: List[CartItem]

class RetrieveCartRequest(BaseModel):
    cart_id: str = Field(..., max_length=100)

# --- App ---
app = FastAPI(title="Shopping Cart Service")

# Middleware to limit request body size to prevent resource exhaustion (DoS)
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    # Limit body to 1MB
    MAX_SIZE = 1024 * 1024 
    content_length = request.headers.get('content-length')
    if content_length and int(content_length) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="Request body too large")
    return await call_next(request)

@app.post("/create_cart", response_model=CreateCartResponse, status_code=status.HTTP_201_CREATED)
async def create_cart():
    try:
        cart_id = str(uuid.uuid4())
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            # Parameterized query prevents SQL injection
            cursor.execute("INSERT INTO carts (cart_id) VALUES (?)", (cart_id,))
            conn.commit()
        return {"cart_id": cart_id}
    except Exception:
        # Generic error handling to prevent leaking internal stack traces
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/add_to_cart")
async def add_to_cart(request: AddToCartRequest):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            
            # Check if cart exists using parameterized query
            cursor.execute("SELECT 1 FROM carts WHERE cart_id = ?", (request.cart_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Cart not found")
            
            # Get current count using parameterized query
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
                # Update or Insert using parameterized query
                # SQLite 3.24+ supports UPSERT (ON CONFLICT)
                cursor.execute(
                    "INSERT INTO cart_items (cart_id, item_id, count) VALUES (?, ?, ?) "
                    "ON CONFLICT(cart_id, item_id) DO UPDATE SET count = excluded.count",
                    (request.cart_id, request.item_id, new_count)
                )
            
            conn.commit()
        return {"message": "Item added or removed successfully"}
    except HTTPException as he:
        raise he
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request")

@app.post("/retrieve_cart", response_model=RetrieveCartResponse)
async def retrieve_cart(request: RetrieveCartRequest):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            
            # Check if cart exists using parameterized query
            cursor.execute("SELECT 1 FROM carts WHERE cart_id = ?", (request.cart_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Cart not found")
            
            # Parameterized query to retrieve items
            cursor.execute(
                "SELECT item_id, count FROM cart_items WHERE cart_id = ?", 
                (request.cart_id,)
            )
            rows = cursor.fetchall()
            
            items = [CartItem(item_id=row[0], count=row[1]) for row in rows]
            return {"items": items}
    except HTTPException as he:
        raise he
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    # Ensure we bind to 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)