import sqlite3
import json
import os
import uvicorn
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict

app = FastAPI(title="Product Catalog")

DB_FILE = "db.sqlite3"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # We store the product name as the primary key and the unstructured properties as a JSON string
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

class SearchResult(BaseModel):
    model_config = ConfigDict(extra='allow')
    name: str

class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]

@app.post("/add", status_code=201)
async def add_product(product: ProductAdd):
    # Extract all fields except 'name' to store as unstructured properties
    data = product.model_dump()
    name = data.pop('name')
    properties_json = json.dumps(data)
    
    try:
        with get_db_connection() as conn:
            conn.execute("INSERT INTO products (name, properties) VALUES (?, ?)", (name, properties_json))
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Product with this name already exists")
    
    return None

@app.get("/download", response_model=ProductDownloadResponse)
async def download_product(name: str = Query(...)):
    with get_db_connection() as conn:
        row = conn.execute("SELECT properties FROM products WHERE name = ?", (name,)).fetchone()
        if row is None:
            raise HTTPException(status_code=400, detail="Product not found")
        
        # The schema asks for the "data of a product" as a string. 
        # We return the JSON representation of the product including its name and properties.
        props = json.loads(row['properties'])
        full_data = {"name": name, **props}
        return {"data": json.dumps(full_data)}

@app.post("/upload")
async def upload_product(payload: ProductUpload):
    try:
        # The data must be in the format returned by /download (a JSON string)
        product_data = json.loads(payload.data)
        if not isinstance(product_data, dict) or "name" not in product_data:
            raise ValueError("Invalid data format")
        
        # Ensure the name in the data matches the name in the request
        if product_data["name"] != payload.name:
            raise ValueError("Name mismatch")
            
        # Extract properties (everything except name)
        props = {k: v for k, v in product_data.items() if k != "name"}
        properties_json = json.dumps(props)
        
        with get_db_connection() as conn:
            conn.execute("INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)", (payload.name, properties_json))
            conn.commit()
            
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid upload query")
        
    return {"message": "The product with the given name was updated."}

@app.get("/search", response_model=SearchResponse)
async def search_products(query: str = Query(...)):
    results = []
    with get_db_connection() as conn:
        rows = conn.execute("SELECT name, properties FROM products").fetchall()
        for row in rows:
            name = row['name']
            props = json.loads(row['properties'])
            
            # Search in name or any property value
            match = (query.lower() in name.lower())
            if not match:
                for val in props.values():
                    if isinstance(val, str) and query.lower() in val.lower():
                        match = True
                        break
            
            if match:
                product_entry = {"name": name, **props}
                results.append(product_entry)
                
    return {"results": results}

if __name__ == "__main__":
    init_db()
    uvicorn.run(app, host="0.0.0.0", port=5000)