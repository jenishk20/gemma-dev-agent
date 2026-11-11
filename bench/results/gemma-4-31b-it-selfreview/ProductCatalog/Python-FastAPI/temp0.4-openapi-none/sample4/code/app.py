import sqlite3
import json
import os
from typing import Dict, List, Any
from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Product Catalog")

DB_PATH = "db.sqlite3"
# Limit request body size to prevent resource exhaustion (e.g., 1MB)
MAX_BODY_SIZE = 1 * 1024 * 1024 

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                name TEXT PRIMARY KEY,
                properties TEXT
            )
        """)
        conn.commit()

@app.on_event("startup")
def startup_event():
    init_db()

# Middleware to enforce request body size limits to prevent resource exhaustion
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    if request.method == "POST":
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_BODY_SIZE:
            raise HTTPException(status_code=400, detail="Request body too large")
    return await call_next(request)

@app.post("/add", status_code=201)
async def add_product(payload: Dict[str, Any]):
    # Input validation: ensure 'name' exists and is a string
    if "name" not in payload:
        raise HTTPException(status_code=400, detail="Missing required field: name")
    
    name = payload["name"]
    if not isinstance(name, str):
        raise HTTPException(status_code=400, detail="Name must be a string")

    # Validate all additional properties are strings to prevent type-injection/unexpected types
    properties = {}
    for k, v in payload.items():
        if k != "name":
            if not isinstance(k, str) or not isinstance(v, str):
                raise HTTPException(status_code=400, detail=f"Property {k} must be a string")
            properties[k] = v

    try:
        with get_db_connection() as conn:
            # Use parameterized query to prevent SQL Injection
            conn.execute("INSERT INTO products (name, properties) VALUES (?, ?)", 
                         (name, json.dumps(properties)))
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Product with this name already exists")
    except Exception:
        # Generic catch to prevent leaking internal database stack traces
        raise HTTPException(status_code=400, detail="Internal server error occurred while adding product")
    
    return None

@app.get("/download")
async def download_product(name: str = Query(...)):
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    try:
        with get_db_connection() as conn:
            # Parameterized query to prevent SQL Injection
            row = conn.execute("SELECT properties FROM products WHERE name = ?", (name,)).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Product not found")
            
            props = json.loads(row['properties'])
            full_data = {"name": name, **props}
            return {"data": json.dumps(full_data)}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Error retrieving product data")

@app.post("/upload", status_code=200)
async def upload_product(payload: Dict[str, Any]):
    if "name" not in payload or "data" not in payload:
        raise HTTPException(status_code=400, detail="Invalid upload query")
    
    name = payload["name"]
    data_str = payload["data"]
    
    if not isinstance(name, str) or not isinstance(data_str, str):
        raise HTTPException(status_code=400, detail="Invalid input types")

    try:
        # Safe JSON deserialization
        data_obj = json.loads(data_str)
        if not isinstance(data_obj, dict) or "name" not in data_obj:
            raise ValueError("Invalid data format")
        
        properties = {k: v for k, v in data_obj.items() if k != "name"}
        
        # Strict type checking for unstructured properties
        for k, v in properties.items():
            if not isinstance(k, str) or not isinstance(v, str):
                raise ValueError("All properties must be strings")

        with get_db_connection() as conn:
            # Parameterized query to prevent SQL Injection
            conn.execute("INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)", 
                         (name, json.dumps(properties)))
            conn.commit()
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid upload query")
    except Exception:
        raise HTTPException(status_code=400, detail="Internal server error occurred during upload")

    return {"message": "The product with the given name was updated."}

@app.get("/search")
async def search_products(query: str = Query(...)):
    if not query:
        raise HTTPException(status_code=400, detail="Invalid search query")

    results = []
    try:
        with get_db_connection() as conn:
            # We fetch all and filter in Python to avoid complex dynamic SQL construction 
            # that could lead to injection if not handled carefully.
            rows = conn.execute("SELECT name, properties FROM products").fetchall()
            for row in rows:
                name = row['name']
                props = json.loads(row['properties'])
                
                # Case-sensitive substring match as per standard 'in' operator
                # This avoids using regex which could lead to ReDoS
                match = (query in name) or any(query in str(v) for v in props.values())
                
                if match:
                    product_entry = {"name": name}
                    product_entry.update(props)
                    results.append(product_entry)
                    
        return {"results": results}
    except Exception:
        raise HTTPException(status_code=400, detail="Error processing search query")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)