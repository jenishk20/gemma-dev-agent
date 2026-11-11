import os
import json
import sqlite3
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI(title="Product Catalog")

DB_PATH = "db.sqlite3"

# Resource Exhaustion: Limit request body size to prevent memory exhaustion
# FastAPI/Starlette doesn't have a built-in global limit for JSON bodies easily,
# but we can implement a middleware to check Content-Length.
class LimitSizeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_size: int = 10 * 1024 * 1024): # 10MB limit
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            if int(content_length) > self.max_size:
                raise HTTPException(status_code=400, detail="Request body too large")
        return await call_next(request)

app.add_middleware(LimitSizeMiddleware)

def get_db_connection():
    # SQL Injection prevention: We use sqlite3.connect and parameterized queries.
    # The DB_PATH is a hardcoded constant, preventing path traversal.
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
        # Error handling: prevent leaking internal DB errors to the user
        pass

init_db()

class ProductAdd(BaseModel):
    name: str
    model_config = {"extra": "allow"}

class ProductUpload(BaseModel):
    name: str
    data: str

class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]

@app.post("/add", status_code=201)
async def add_product(product: ProductAdd):
    product_data = product.model_dump()
    name = product_data.pop("name")
    
    # Deserialization/Serialization: json.dumps is safe. 
    # We ensure only string values are stored as per OpenAPI schema.
    # The schema says additionalProperties are strings.
    for k, v in product_data.items():
        if not isinstance(v, (str, int, float, bool, type(None))):
            raise HTTPException(status_code=400, detail="Invalid property type")
        product_data[k] = str(v)

    properties_json = json.dumps(product_data)
    
    try:
        with get_db_connection() as conn:
            # SQL Injection: Using parameterized query (?)
            conn.execute("INSERT INTO products (name, properties) VALUES (?, ?)", (name, properties_json))
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Product with this name already exists")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid input")
    
    return None

@app.get("/download")
async def download_product(name: str = Query(...)):
    try:
        with get_db_connection() as conn:
            # SQL Injection: Using parameterized query (?)
            row = conn.execute("SELECT properties FROM products WHERE name = ?", (name,)).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Product not found")
            
            properties = json.loads(row["properties"])
            full_product = {"name": name, **properties}
            return {"data": json.dumps(full_product)}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Internal error")

@app.post("/upload")
async def upload_product(payload: ProductUpload):
    try:
        # Deserialization: json.loads is safe for JSON. 
        # We validate the structure immediately after loading.
        product_dict = json.loads(payload.data)
        if not isinstance(product_dict, dict) or "name" not in product_dict:
            raise ValueError("Invalid product data")
        
        if product_dict["name"] != payload.name:
            raise ValueError("Name mismatch")
            
        props = {k: v for k, v in product_dict.items() if k != "name"}
        # Ensure all properties are strings as per schema
        for k, v in props.items():
            props[k] = str(v)
            
        properties_json = json.dumps(props)
        
        with get_db_connection() as conn:
            # SQL Injection: Using parameterized query (?)
            conn.execute("INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)", 
                         (payload.name, properties_json))
            conn.commit()
            
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid upload query")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid upload query")
    
    return {"message": "The product with the given name was updated."}

@app.get("/search", response_model=SearchResponse)
async def search_products(query: str = Query(...)):
    # Resource Exhaustion: Limit the query length to prevent ReDoS or memory issues
    if len(query) > 1000:
        raise HTTPException(status_code=400, detail="Search query too long")

    results = []
    try:
        with get_db_connection() as conn:
            # SQL Injection: Using parameterized query (?)
            cursor = conn.execute("SELECT name, properties FROM products")
            for row in cursor:
                name = row["name"]
                properties = json.loads(row["properties"])
                
                # Case-insensitive search. 
                # We use 'in' operator on strings, which is safe from regex injection.
                q_lower = query.lower()
                match = (q_lower in name.lower()) or \
                        any(q_lower in str(val).lower() for val in properties.values())
                
                if match:
                    product_entry = {"name": name, **properties}
                    results.append(product_entry)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid search query")
                
    return {"results": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)