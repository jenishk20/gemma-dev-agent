import os
import json
import sqlite3
from typing import Dict, List, Any
from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI(title="Product Catalog")

DB_PATH = "db.sqlite3"

# Resource Exhaustion: Limit the size of the request body to prevent memory exhaustion
MAX_BODY_SIZE = 1 * 1024 * 1024  # 1 MB

class LimitBodySizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            if int(content_length) > MAX_BODY_SIZE:
                raise HTTPException(status_code=400, detail="Request body too large")
        
        # For cases where content-length is missing or lied about, 
        # we wrap the stream reading in the route handlers or rely on FastAPI's default 
        # but here we implement a basic check.
        return await call_next(request)

app.add_middleware(LimitBodySizeMiddleware)

def get_db_connection():
    # Using a fixed path for the DB prevents path traversal
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        with get_db_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    name TEXT PRIMARY KEY,
                    properties TEXT
                )
            """)
            conn.commit()
    except Exception:
        # Error handling: avoid leaking internal DB errors to the user
        pass

init_db()

class ProductCreate(BaseModel):
    name: str
    model_config = {"extra": "allow"}

class ProductUpload(BaseModel):
    name: str
    data: str

class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]

@app.post("/add", status_code=201)
async def add_product(product: ProductCreate):
    try:
        data = product.model_dump()
        name = data.pop("name")
        
        # Ensure all values are strings as per OpenAPI schema
        # This also prevents injection of complex types into the JSON blob
        properties = {k: str(v) for k, v in data.items()}
        props_json = json.dumps(properties)

        with get_db_connection() as conn:
            # SQL Injection Prevention: Use parameterized queries
            conn.execute("INSERT INTO products (name, properties) VALUES (?, ?)", (name, props_json))
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Product with this name already exists")
    except Exception:
        # Error handling: Generic 400 for any other malformed input
        raise HTTPException(status_code=400, detail="Invalid input")
    
    return None

@app.get("/download")
async def download_product(name: str = Query(...)):
    try:
        with get_db_connection() as conn:
            # SQL Injection Prevention: Parameterized query
            row = conn.execute("SELECT properties FROM products WHERE name = ?", (name,)).fetchone()
            
        if row is None:
            raise HTTPException(status_code=400, detail="Product not found")
        
        props = json.loads(row["properties"])
        full_product = {"name": name, **props}
        return {"data": json.dumps(full_product)}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request")

@app.post("/upload")
async def upload_product(payload: ProductUpload):
    try:
        # Deserialization: json.loads is safe for standard JSON
        product_data = json.loads(payload.data)
        if not isinstance(product_data, dict) or "name" not in product_data:
            raise ValueError("Invalid data format")
        
        if product_data["name"] != payload.name:
            raise ValueError("Name mismatch")

        name = product_data.pop("name")
        properties = {k: str(v) for k, v in product_data.items()}
        props_json = json.dumps(properties)

        with get_db_connection() as conn:
            # SQL Injection Prevention: Parameterized query
            conn.execute("INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)", (name, props_json))
            conn.commit()
            
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid upload query")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid upload query")

    return {"message": "The product with the given name was updated."}

@app.get("/search")
async def search_products(query: str = Query(...)):
    try:
        results = []
        with get_db_connection() as conn:
            # We fetch all and filter in Python to avoid complex dynamic SQL 
            # and potential SQL injection via LIKE clauses if not handled carefully.
            rows = conn.execute("SELECT name, properties FROM products").fetchall()
            
        query_lower = query.lower()
        for row in rows:
            name = row["name"]
            props = json.loads(row["properties"])
            
            # Case-insensitive search in name or values
            match = (query_lower in name.lower()) or any(query_lower in str(v).lower() for v in props.values())
            
            if match:
                product_obj = {"name": name, **props}
                results.append(product_obj)

        return {"results": results}
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid search query")

if __name__ == "__main__":
    import uvicorn
    # Port 5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)