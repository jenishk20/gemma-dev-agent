import sqlite3
import uuid
import os
from typing import List
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

# --- Database Setup ---
DB_PATH = "db.sqlite3"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # Carts table stores the cart_id
        conn.execute("CREATE TABLE IF NOT EXISTS carts (cart_id TEXT PRIMARY KEY)")
        # CartItems table stores the mapping of cart to items
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

# --- App Initialization ---
app = FastAPI(title="Shopping Cart Service")

@app.on_event("startup")
def startup_event():
    init_db()

# --- Endpoints ---

@app.post("/create_cart", response_model=CreateCartResponse, status_code=status.HTTP_201_CREATED)
async def create_cart():
    """Create a new shopping cart"""
    cart_id = str(uuid.uuid4())
    try:
        with get_db_connection() as conn:
            conn.execute("INSERT INTO carts (cart_id) VALUES (?)", (cart_id,))
            conn.commit()
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail="Database error occurred")
    
    return {"cart_id": cart_id}

@app.post("/add_to_cart", status_code=status.HTTP_200_OK)
async def add_to_cart(request: AddToCartRequest):
    """Add or remove items from the cart"""
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

        if new_count <= 0:
            # Remove item from cart if count drops to 0 or below
            conn.execute("DELETE FROM cart_items WHERE cart_id = ? AND item_id = ?", 
                         (request.cart_id, request.item_id))
        else:
            # Upsert item count
            conn.execute("""
                INSERT INTO cart_items (cart_id, item_id, count) 
                VALUES (?, ?, ?) 
                ON CONFLICT(cart_id, item_id) DO UPDATE SET count = excluded.count
            """, (request.cart_id, request.item_id, new_count))
        
        conn.commit()
    
    return None # Returns 200 OK

@app.post("/retrieve_cart", response_model=RetrieveCartResponse)
async def retrieve_cart(request: BaseModel):
    # Using a generic BaseModel to handle the request body containing cart_id
    # since the schema specifies a POST request with a body
    cart_id = getattr(request, 'cart_id', None)
    if cart_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="cart_id is required")

    with get_db_connection() as conn:
        # Verify cart exists
        cursor = conn.execute("SELECT 1 FROM carts WHERE cart_id = ?", (cart_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

        # Retrieve items
        cursor = conn.execute("SELECT item_id, count FROM cart_items WHERE cart_id = ?", (cart_id,))
        items = [{"item_id": row['item_id'], "count": row['count']} for row in cursor.fetchall()]
        
    return {"items": items}

# Override retrieve_cart to match the specific schema requirement for the request body
# The schema defines retrieve_cart as a POST with a body containing cart_id
class RetrieveCartRequest(BaseModel):
    cart_id: str

@app.post("/retrieve_cart", response_model=RetrieveCartResponse)
async def retrieve_cart_fixed(request: RetrieveCartRequest):
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT 1 FROM carts WHERE cart_id = ?", (request.cart_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

        cursor = conn.execute("SELECT item_id, count FROM cart_items WHERE cart_id = ?", (request.cart_id,))
        items = [{"item_id": row['item_id'], "count": row['count']} for row in cursor.fetchall()]
        
    return {"items": items}

# Note: The duplicate function definition above is to ensure the Pydantic model is correctly mapped.
# FastAPI will use the last defined function for the route.

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)