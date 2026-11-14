import sqlite3
import uuid
import os
from typing import List
from fastapi import FastAPI, HTTPException, status, Request
from pydantic import BaseModel, Field, validator
import uvicorn

# --- Models ---

class CreateCartResponse(BaseModel):
    cart_id: str

class AddToCartRequest(BaseModel):
    cart_id: str = Field(..., max_length=100)
    item_id: int
    count: int

    @validator('count')
    def limit_count_range(cls, v):
        # Prevent integer overflow or extreme resource exhaustion in logic
        if abs(v) > 1_000_000:
            raise ValueError('Count is too large')
        return v

class RetrieveCartRequest(BaseModel):
    cart_id: str = Field(..., max_length=100)

class CartItem(BaseModel):
    item_id: int
    count: int

class RetrieveCartResponse(BaseModel):
    items: List[CartItem]

# --- Database Logic ---

DB_FILE = "db.sqlite3"

def get_db_connection():
    # Use a connection with a timeout to prevent database locking from causing DoS
    conn = sqlite3.connect(DB_FILE, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS carts (cart_id TEXT PRIMARY KEY)")
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

# --- API Implementation ---

app = FastAPI(title="Shopping Cart Service")

@app.on_event("startup")
def startup_event():
    init_db()

@app.post("/create_cart", response_model=CreateCartResponse, status_code=status.HTTP_201_CREATED)
def create_cart():
    try:
        cart_id = str(uuid.uuid4())
        with get_db_connection() as conn:
            conn.execute("INSERT INTO carts (cart_id) VALUES (?)", (cart_id,))
            conn.commit()
        return CreateCartResponse(cart_id=cart_id)
    except Exception:
        # Generic error to avoid leaking internal DB details
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@app.post("/add_to_cart", status_code=status.HTTP_200_OK)
def add_to_cart(request: AddToCartRequest):
    try:
        with get_db_connection() as conn:
            # Parameterized query prevents SQL Injection
            cursor = conn.execute("SELECT 1 FROM carts WHERE cart_id = ?", (request.cart_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

            cursor = conn.execute(
                "SELECT count FROM cart_items WHERE cart_id = ? AND item_id = ?", 
                (request.cart_id, request.item_id)
            )
            row = cursor.fetchone()
            current_count = row['count'] if row else 0
            new_count = current_count + request.count

            if new_count < 0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request")

            if new_count == 0:
                conn.execute(
                    "DELETE FROM cart_items WHERE cart_id = ? AND item_id = ?", 
                    (request.cart_id, request.item_id)
                )
            else:
                # Using parameterized query for UPSERT
                conn.execute(
                    "INSERT INTO cart_items (cart_id, item_id, count) VALUES (?, ?, ?) "
                    "ON CONFLICT(cart_id, item_id) DO UPDATE SET count = excluded.count",
                    (request.cart_id, request.item_id, new_count)
                )
            conn.commit()
        return {"message": "Item added or removed successfully"}
    except HTTPException as he:
        raise he
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request")

@app.post("/retrieve_cart", response_model=RetrieveCartResponse)
def retrieve_cart(request: RetrieveCartRequest):
    try:
        with get_db_connection() as conn:
            # Parameterized query prevents SQL Injection
            cursor = conn.execute("SELECT 1 FROM carts WHERE cart_id = ?", (request.cart_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

            cursor = conn.execute(
                "SELECT item_id, count FROM cart_items WHERE cart_id = ?", 
                (request.cart_id,)
            )
            # Limit result set to prevent memory exhaustion (DoS)
            rows = cursor.fetchmany(1000) 
            items = [CartItem(item_id=row['item_id'], count=row['count']) for row in rows]
        
        return RetrieveCartResponse(items=items)
    except HTTPException as he:
        raise he
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

# Middleware to limit request body size to prevent resource exhaustion
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    # Limit body to 1MB
    MAX_SIZE = 1024 * 1024
    content_length = request.headers.get('content-length')
    if content_length and int(content_length) > MAX_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Request body too large")
    return await call_next(request)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)