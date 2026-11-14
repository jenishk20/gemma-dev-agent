import sqlite3
import json
import os
import uvicorn
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict

app = FastAPI(title="Product Catalog")

DB_FILE = "db.sqlite3"

# Resource exhaustion: Limit request body size to prevent MemoryError/DoS
# FastAPI/Starlette doesn't have a simple global limit, but we can check content length
# or rely on the server config. For this implementation, we use a middleware approach.
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    # Limit request body to 1MB to prevent resource exhaustion
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 1024 * 1024:
        raise HTTPException(status_code=400, detail="Request body too large")
    return await call_next(request)

def get_db_connection():
    # Using a context manager for the connection is handled in the routes
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # SQL Injection prevention: Table creation is static
        conn.execute(
            "CREATE TABLE IF NOT EXISTS products (name TEXT PRIMARY KEY, properties TEXT)"
        )
        conn.commit()

# Pydantic models for request/response validation
class ProductAdd(BaseModel):
    model_config = ConfigDict(extra='allow')
    name: str

class ProductUpload(BaseModel):
    name: str
    data: str

class ProductDownloadResponse(BaseModel):
    data: str

class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]

@app.post("/add", status_code=201)
async def add_product(product: ProductAdd):
    # Extract all fields except 'name' to store as unstructured properties
    data = product.model_dump()
    name = data.pop('name')
    
    # Ensure all additional properties are strings as per OpenAPI schema
    # This prevents non-string types from causing issues during search/serialization
    for k, v in data.items():
        if not isinstance(v, str):
            raise HTTPException(status_code=400, detail="Invalid input: properties must be strings")
    
    properties_json = json.dumps(data)
    
    try:
        with get_db_connection() as conn:
            # SQL Injection prevention: Using parameterized queries
            conn.execute("INSERT INTO products (name, properties) VALUES (?, ?)", (name, properties_json))
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Product with this name already exists")
    except Exception:
        # Error handling: Catch unexpected exceptions to prevent leaking stack traces
        raise HTTPException(status_code=400, detail="Invalid input")
    
    return None

@app.get("/download", response_model=ProductDownloadResponse)
async def download_product(name: str = Query(...)):
    try:
        with get_db_connection() as conn:
            # SQL Injection prevention: Using parameterized queries
            row = conn.execute("SELECT properties FROM products WHERE name = ?", (name,)).fetchone()
            if row is None:
                raise HTTPException(status_code=400, detail="Product not found")
            
            props = json.loads(row['properties'])
            full_data = {"name": name, **props}
            return {"data": json.dumps(full_data)}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid input")

@app.post("/upload")
async def upload_product(payload: ProductUpload):
    try:
        # Deserialization: json.loads is safe for standard JSON. 
        # We validate the structure immediately after.
        product_data = json.loads(payload.data)
        if not isinstance(product_data, dict) or "name" not in product_data:
            raise ValueError("Invalid data format")
        
        if product_data["name"] != payload.name:
            raise ValueError("Name mismatch")
            
        # Validate that all properties are strings as per schema
        props = {k: v for k, v in product_data.items() if k != "name"}
        for v in props.values():
            if not isinstance(v, str):
                raise ValueError("Properties must be strings")
                
        properties_json = json.dumps(props)
        
        with get_db_connection() as conn:
            # SQL Injection prevention: Using parameterized queries
            conn.execute("INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)", (payload.name, properties_json))
            conn.commit()
            
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid upload query")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid upload query")
        
    return {"message": "The product with the given name was updated."}

@app.get("/search", response_model=SearchResponse)
async def search_products(query: str = Query(...)):
    try:
        results = []
        with get_db_connection() as conn:
            # We fetch all and filter in Python to avoid complex dynamic SQL and potential injection
            # Resource exhaustion: In a production app, we would use LIMIT/OFFSET.
            # Here we maintain the requested behavior but keep the query parameterized.
            rows = conn.execute("SELECT name, properties FROM products").fetchall()
            
            # Case-insensitive search as per typical catalog behavior
            search_term = query.lower()
            
            for row in rows:
                name = row['name']
                props = json.loads(row['properties'])
                
                match = (search_term in name.lower())
                if not match:
                    for val in props.values():
                        if isinstance(val, str) and search_term in val.lower():
                            match = True
                            break
                
                if match:
                    product_entry = {"name": name, **props}
                    results.append(product_entry)
                    
        return {"results": results}
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid search query")

if __name__ == "__main__":
    init_db()
    # Port 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)