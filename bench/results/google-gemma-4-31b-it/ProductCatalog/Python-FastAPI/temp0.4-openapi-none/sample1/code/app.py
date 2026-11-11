import os
import json
import sqlite3
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

app = FastAPI(title="Product Catalog")

DB_PATH = "db.sqlite3"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # We store the product name and a JSON string of all properties
        # This allows for "unstructured" properties as requested
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                name TEXT PRIMARY KEY,
                properties TEXT
            )
        """)
        conn.commit()

init_db()

class ProductAdd(BaseModel):
    name: str
    # Use extra='allow' to handle additionalProperties from OpenAPI
    model_config = {"extra": "allow"}

class ProductUpload(BaseModel):
    name: str
    data: str

class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]

@app.post("/add", status_code=201)
async def add_product(product: ProductAdd):
    # Extract all fields into a dictionary
    product_data = product.model_dump()
    name = product_data.pop("name")
    
    # Store the remaining properties as a JSON string
    properties_json = json.dumps(product_data)
    
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
        
        # The schema asks for a JSON object with a 'data' field containing the product data as a string
        # We return the JSON representation of the product's unstructured properties
        properties = json.loads(row["properties"])
        # Reconstruct the full object including the name for the data string
        full_product = {"name": name, **properties}
        return {"data": json.dumps(full_product)}

@app.post("/upload")
async def upload_product(payload: ProductUpload):
    try:
        # The data string must be a valid JSON representation of the product
        product_dict = json.loads(payload.data)
        if not isinstance(product_dict, dict) or "name" not in product_dict:
            raise ValueError("Invalid product data")
        
        # Ensure the name in the data matches the name in the request body
        if product_dict["name"] != payload.name:
            raise ValueError("Name mismatch between body and data")
            
        # Extract properties (everything except name)
        props = {k: v for k, v in product_dict.items() if k != "name"}
        properties_json = json.dumps(props)
        
        with get_db_connection() as conn:
            conn.execute("INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)", 
                         (payload.name, properties_json))
            conn.commit()
            
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid upload query")
    
    return {"message": "The product with the given name was updated."}

@app.get("/search", response_model=SearchResponse)
async def search_products(query: str = Query(...)):
    results = []
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT name, properties FROM products")
        for row in cursor:
            name = row["name"]
            properties = json.loads(row["properties"])
            
            # Check if query matches name or any value in the unstructured properties
            match = (query.lower() in name.lower()) or \
                    any(query.lower() in str(val).lower() for val in properties.values())
            
            if match:
                product_entry = {"name": name, **properties}
                results.append(product_entry)
                
    return {"results": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)