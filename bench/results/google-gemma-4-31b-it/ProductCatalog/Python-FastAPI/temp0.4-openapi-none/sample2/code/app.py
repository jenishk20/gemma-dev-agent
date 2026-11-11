import sqlite3
import json
import os
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

app = FastAPI(title="Product Catalog")

DB_FILE = "db.sqlite3"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # We store the product name as the primary key and the unstructured 
        # properties as a JSON string in a single column.
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
    # Pydantic allows capturing extra fields via model_extra if configured, 
    # but for simplicity in a dynamic schema, we use a Dict or allow extra.
    model_config = {"extra": "allow"}

class ProductUpload(BaseModel):
    name: str
    data: str

@app.post("/add", status_code=201)
async def add_product(product: ProductAdd):
    # Extract all fields except 'name' into a dictionary
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
        raise HTTPException(status_code=400, detail="Product not found")
    
    # The schema requires returning an object with a 'data' field containing the product data
    # Based on the requirement "returned by the /download endpoint", we return the JSON string of properties.
    return {"data": row["properties"]}

@app.post("/upload")
async def upload_product(payload: ProductUpload):
    try:
        # Validate that 'data' is a valid JSON string
        properties_json = payload.data
        json.loads(properties_json) 
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format in data field")

    with get_db_connection() as conn:
        cursor = conn.execute("UPDATE products SET properties = ? WHERE name = ?", (properties_json, payload.name))
        conn.commit()
        
        if cursor.rowcount == 0:
            # If the product doesn't exist, the prompt says "fully replaces any previous data", 
            # usually implying an upsert or that the product must exist. 
            # Given the context of "upload data for a product... in the catalog", we assume it must exist.
            raise HTTPException(status_code=400, detail="Product not found in catalog")
            
    return {"message": "The product with the given name was updated."}

@app.get("/search")
async def search_products(query: str = Query(...)):
    results = []
    with get_db_connection() as conn:
        rows = conn.execute("SELECT name, properties FROM products").fetchall()
        
        for row in rows:
            name = row["name"]
            props = json.loads(row["properties"])
            
            # Search in name or any of the values in the unstructured properties
            match = (query.lower() in name.lower()) or any(
                query.lower() in str(val).lower() for val in props.values()
            )
            
            if match:
                # Combine name and properties into one object
                product_obj = {"name": name}
                product_obj.update(props)
                results.append(product_obj)
                
    return {"results": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)