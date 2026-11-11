import os
import json
import sqlite3
from typing import Dict, List, Any
from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field

app = FastAPI(title="Product Catalog")

DB_PATH = "db.sqlite3"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # We store the product name as the primary key.
        # The unstructured properties are stored as a JSON string in the 'properties' column.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                name TEXT PRIMARY KEY,
                properties TEXT
            )
        """)
        conn.commit()

@app.on_event("startup")
async def startup_event():
    init_db()

class ProductCreate(BaseModel):
    name: str
    # Using Dict[str, str] to handle additionalProperties: type: string
    # We allow extra fields via model_config or by capturing them.
    # Since the schema says 'name' is required and others are additional, 
    # we use a flexible model.
    model_config = {"extra": "allow"}

class UploadRequest(BaseModel):
    name: str
    data: str

class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]

@app.post("/add", status_code=status.HTTP_201_CREATED)
async def add_product(product: ProductCreate):
    # Extract name and all other fields
    data = product.model_dump()
    name = data.pop("name")
    
    # Ensure all additional properties are strings as per schema
    for k, v in data.items():
        if not isinstance(v, str):
            raise HTTPException(status_code=400, detail=f"Property {k} must be a string")

    properties_json = json.dumps(data)
    
    try:
        with get_db_connection() as conn:
            conn.execute("INSERT INTO products (name, properties) VALUES (?, ?)", (name, properties_json))
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Product with this name already exists")
    
    return None

@app.get("/download")
async def download_product(name: str = Query(...)):
    with get_db_connection() as conn:
        row = conn.execute("SELECT properties FROM products WHERE name = ?", (name,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # The schema expects a JSON object with a 'data' field containing the string representation
        return {"data": row["properties"]}

@app.post("/upload")
async def upload_product(request: UploadRequest):
    try:
        # Validate that the data is a valid JSON string of properties
        props = json.loads(request.data)
        if not isinstance(props, dict):
            raise ValueError()
        for v in props.values():
            if not isinstance(v, str):
                raise ValueError()
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid upload query: data must be a JSON object of strings")

    with get_db_connection() as conn:
        # Use REPLACE to fully replace previous data for the product
        conn.execute("INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)", 
                     (request.name, request.data))
        conn.commit()
    
    return {"message": "The product with the given name was updated."}

@app.get("/search", response_model=SearchResponse)
async def search_products(query: str = Query(...)):
    if not query:
        raise HTTPException(status_code=400, detail="Invalid search query")

    results = []
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT name, properties FROM products")
        for row in cursor:
            name = row["name"]
            properties = json.loads(row["properties"])
            
            # Match name or any property value
            match = (query in name)
            if not match:
                for val in properties.values():
                    if query in val:
                        match = True
                        break
            
            if match:
                product_obj = {"name": name}
                product_obj.update(properties)
                results.append(product_obj)
                
    return {"results": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)