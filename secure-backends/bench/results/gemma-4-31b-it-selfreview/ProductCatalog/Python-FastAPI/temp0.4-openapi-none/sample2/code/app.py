import sqlite3
import json
import os
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field

app = FastAPI(title="Product Catalog")

DB_FILE = "db.sqlite3"

# Resource exhaustion: Limit the size of the request body to prevent memory exhaustion
# FastAPI/Starlette doesn't have a built-in global body limit middleware that is simple 
# without custom middleware, but we can implement a basic check or rely on the 
# server configuration. For this implementation, we will use a middleware to 
# check Content-Length.
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    # Limit request body to 1MB to prevent resource exhaustion
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 1024 * 1024:
        raise HTTPException(status_code=400, detail="Request body too large")
    return await call_next(request)

def get_db_connection():
    # Using a local connection per request to avoid threading issues with sqlite3
    conn = sqlite3.connect(DB_FILE)
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
        # Error handling: avoid leaking internal DB details to the user
        pass

init_db()

class ProductAdd(BaseModel):
    name: str
    model_config = {"extra": "allow"}

class ProductUpload(BaseModel):
    name: str
    data: str

@app.post("/add", status_code=201)
async def add_product(product: ProductAdd):
    # Input validation: Ensure name is not empty or just whitespace
    if not product.name or not product.name.strip():
        raise HTTPException(status_code=400, detail="Invalid input: name is required")

    product_data = product.model_dump()
    name = product_data.pop("name")
    
    # Ensure all additional properties are strings as per OpenAPI schema
    # This prevents non-string types from being injected into the JSON store
    for key, value in product_data.items():
        if not isinstance(value, str):
            raise HTTPException(status_code=400, detail=f"Property {key} must be a string")

    properties_json = json.dumps(product_data)
    
    try:
        with get_db_connection() as conn:
            # SQL Injection prevention: using parameterized queries (?)
            conn.execute("INSERT INTO products (name, properties) VALUES (?, ?)", (name, properties_json))
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Product with this name already exists")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid input")
    
    return None

@app.get("/download")
async def download_product(name: str = Query(...)):
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="Invalid input")

    try:
        with get_db_connection() as conn:
            # SQL Injection prevention: parameterized query
            row = conn.execute("SELECT properties FROM products WHERE name = ?", (name,)).fetchone()
    except Exception:
        raise HTTPException(status_code=400, detail="Internal error")
        
    if row is None:
        raise HTTPException(status_code=400, detail="Product not found")
    
    return {"data": row["properties"]}

@app.post("/upload")
async def upload_product(payload: ProductUpload):
    if not payload.name or not payload.name.strip():
        raise HTTPException(status_code=400, detail="Invalid upload query")

    try:
        # Deserialization check: Ensure the data is valid JSON and consists of string values
        # as per the schema requirements for unstructured properties.
        properties_json = payload.data
        parsed_data = json.loads(properties_json)
        
        if not isinstance(parsed_data, dict):
            raise ValueError("Data must be a JSON object")
        
        for k, v in parsed_data.items():
            if not isinstance(v, str):
                raise ValueError("All properties must be strings")
                
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid upload query")

    try:
        with get_db_connection() as conn:
            # SQL Injection prevention: parameterized query
            cursor = conn.execute("UPDATE products SET properties = ? WHERE name = ?", (properties_json, payload.name))
            conn.commit()
            
            if cursor.rowcount == 0:
                raise HTTPException(status_code=400, detail="Invalid upload query")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid upload query")
            
    return {"message": "The product with the given name was updated."}

@app.get("/search")
async def search_products(query: str = Query(...)):
    if not query:
        raise HTTPException(status_code=400, detail="Invalid search query")

    results = []
    try:
        with get_db_connection() as conn:
            # We fetch and filter in Python to avoid complex SQL LIKE patterns 
            # that could be abused for DoS (regex-like attacks in some DBs)
            rows = conn.execute("SELECT name, properties FROM products").fetchall()
            
            for row in rows:
                name = row["name"]
                try:
                    props = json.loads(row["properties"])
                except json.JSONDecodeError:
                    continue
                
                # Case-insensitive search as per common catalog behavior
                # Use simple string containment to avoid regex injection
                search_term = query.lower()
                match = (search_term in name.lower()) or any(
                    search_term in str(val).lower() for val in props.values()
                )
                
                if match:
                    product_obj = {"name": name}
                    product_obj.update(props)
                    results.append(product_obj)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid search query")
                
    return {"results": results}

if __name__ == "__main__":
    import uvicorn
    # Port 5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)