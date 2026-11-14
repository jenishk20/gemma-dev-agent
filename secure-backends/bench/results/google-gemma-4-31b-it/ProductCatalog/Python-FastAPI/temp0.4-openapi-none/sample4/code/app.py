import sqlite3
import json
import os
from typing import Dict, List, Any
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
import uvicorn

app = FastAPI(title="Product Catalog")

DB_PATH = "db.sqlite3"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # We store the product name as the primary key and the unstructured properties as a JSON string
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

class ProductAdd(BaseModel):
    name: str
    # Pydantic allows capturing additional fields via model_extra if configured, 
    # but for simplicity in FastAPI, we can use a Dict or just accept the raw JSON.
    # Since the schema specifies additionalProperties: string, we handle this in the route.

@app.post("/add", status_code=201)
async def add_product(payload: Dict[str, Any]):
    if "name" not in payload:
        raise HTTPException(status_code=400, detail="Missing required field: name")
    
    name = payload["name"]
    if not isinstance(name, str):
        raise HTTPException(status_code=400, detail="Name must be a string")

    # Filter out 'name' and ensure all other values are strings as per schema
    properties = {}
    for k, v in payload.items():
        if k != "name":
            if not isinstance(v, str):
                raise HTTPException(status_code=400, detail=f"Property {k} must be a string")
            properties[k] = v

    try:
        with get_db_connection() as conn:
            conn.execute("INSERT INTO products (name, properties) VALUES (?, ?)", 
                         (name, json.dumps(properties)))
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
        
        # The schema asks for the data as a string in the 'data' field
        # We return the JSON representation of the properties
        props = json.loads(row['properties'])
        # To make it "the data of a product" as a string, we serialize the whole object including name
        full_data = {"name": name, **props}
        return {"data": json.dumps(full_data)}

@app.post("/upload", status_code=200)
async def upload_product(payload: Dict[str, Any]):
    if "name" not in payload or "data" not in payload:
        raise HTTPException(status_code=400, detail="Invalid upload query: missing name or data")
    
    name = payload["name"]
    data_str = payload["data"]
    
    try:
        data_obj = json.loads(data_str)
        if not isinstance(data_obj, dict) or "name" not in data_obj:
            raise ValueError("Invalid data format")
        
        # The data must replace previous data. We extract properties (everything except name)
        properties = {k: v for k, v in data_obj.items() if k != "name"}
        
        # Validate that all properties are strings
        for v in properties.values():
            if not isinstance(v, str):
                raise ValueError("All properties must be strings")

        with get_db_connection() as conn:
            conn.execute("INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)", 
                         (name, json.dumps(properties)))
            conn.commit()
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid data format")

    return {"message": "The product with the given name was updated."}

@app.get("/search")
async def search_products(query: str = Query(...)):
    if not query:
        raise HTTPException(status_code=400, detail="Invalid search query")

    results = []
    with get_db_connection() as conn:
        rows = conn.execute("SELECT name, properties FROM products").fetchall()
        for row in rows:
            name = row['name']
            props = json.loads(row['properties'])
            
            # Match if query is in name or any of the property values
            match = (query in name) or any(query in str(v) for v in props.values())
            
            if match:
                product_entry = {"name": name}
                product_entry.update(props)
                results.append(product_entry)
                
    return {"results": results}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)