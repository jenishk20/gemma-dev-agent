import sqlite3
import uuid
import os
from typing import List
from fastapi import FastAPI, HTTPException, status, Request
from pydantic import BaseModel, Field

# --- Database Setup ---
DB_FILE = "db.sqlite3"

def get_db_connection():
    # Using a context manager for the connection is handled in the endpoints
    conn = sqlite3.connect(DB_FILE)
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

# Initialize DB on startup
init_db()

# --- FastAPI App ---
app = FastAPI(title="Shopping Cart Service")

# --- Models ---
# Added constraints to prevent resource exhaustion via massive integers or strings
class CreateCartResponse(BaseModel):
    cart_id: str

class AddToCartRequest(BaseModel):
    cart_id: str = Field(..., max_length=100)
    item_id: int = Field(...)
    count: int = Field(...)

class RetrieveCartRequest(BaseModel):
    cart_id: str = Field(..., max_length=100)

class CartItem(BaseModel):
    item_id: int
    count: int

class RetrieveCartResponse(BaseModel):
    items: List[CartItem]

# --- Endpoints ---

@app.post("/create_cart", response_model=CreateCartResponse, status_code=status.HTTP_201_CREATED)
async def create_cart():
    """Create a new shopping cart"""
    # uuid4 provides cryptographically secure randomness
    cart_id = str(uuid.uuid4())
    try:
        with get_db_connection() as conn:
            # Parameterized query prevents SQL injection
            conn.execute("INSERT INTO carts (cart_id) VALUES (?)", (cart_id,))
            conn.commit()
    except Exception:
        # Generic error to avoid leaking internal database details/stack traces
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
    
    return {"cart_id": cart_id}

@app.post("/add_to_cart")
async def add_to_cart(request: AddToCartRequest):
    """Add or remove items from the cart"""
    try:
        with get_db_connection() as conn:
            # Parameterized query prevents SQL injection
            cursor = conn.execute("SELECT 1 FROM carts WHERE cart_id = ?", (request.cart_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

            # Parameterized query prevents SQL injection
            cursor = conn.execute("SELECT count FROM cart_items WHERE cart_id = ? AND item_id = ?", 
                                  (request.cart_id, request.item_id))
            row = cursor.fetchone()
            current_count = row['count'] if row else 0
            
            new_count = current_count + request.count
            
            if new_count < 0:
                # Specification requires 400 for invalid requests
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Item count cannot be negative")

            if new_count == 0:
                conn.execute("DELETE FROM cart_items WHERE cart_id = ? AND item_id = ?", 
                             (request.cart_id, request.item_id))
            else:
                # Parameterized query prevents SQL injection
                conn.execute("""
                    INSERT INTO cart_items (cart_id, item_id, count) 
                    VALUES (?, ?, ?) 
                    ON CONFLICT(cart_id, item_id) DO UPDATE SET count = excluded.count
                """, (request.cart_id, request.item_id, new_count))
            
            conn.commit()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
    
    return None

@app.post("/retrieve_cart", response_model=RetrieveCartResponse)
async def retrieve_cart(request: RetrieveCartRequest):
    """Retrieve all items in the cart"""
    try:
        with get_db_connection() as conn:
            # Parameterized query prevents SQL injection
            cursor = conn.execute("SELECT 1 FROM carts WHERE cart_id = ?", (request.cart_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

            # Parameterized query prevents SQL injection
            cursor = conn.execute("SELECT item_id, count FROM cart_items WHERE cart_id = ?", (request.cart_id,))
            rows = cursor.fetchall()
            
            items = [CartItem(item_id=row['item_id'], count=row['count']) for row in rows]
            return {"items": items}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    # Port 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)