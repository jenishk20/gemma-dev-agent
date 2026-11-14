import sqlite3
import json
import os
from typing import Dict, List, Any
from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, Field

app = FastAPI(title="Product Catalog")

DB_FILE = "db.sqlite3"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # We store the product name as the primary key
        # and the unstructured properties as a JSON string in a 'properties' column
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                name TEXT PRIMARY KEY,
                properties TEXT
            )
        """)
        conn.commit()

# Initialize database on startup
init_db()

class ProductCreate(BaseModel):
    name: str
    # Use a dictionary to capture additionalProperties from the OpenAPI spec
    # Pydantic's extra='allow' would work, but for explicit schema mapping 
    # we handle the input as a dict.
    model_config = {"extra": "allow"}

class ProductUpload(BaseModel):
    name: str
    data: str

@app.post("/add", status_code=201)
async def add_product(product: ProductCreate):
    # Extract all fields except 'name' to store as unstructured properties
    product_dict = product.model_dump()
    name = product_dict.pop("name")
    
    # Ensure all values in properties are strings as per OpenAPI spec
    properties = {k: str(v) for k, v in product_dict.items()}
    props_json = json.dumps(properties)

    try:
        with get_db_connection() as conn:
            conn.execute("INSERT INTO products (name, properties) VALUES (?, ?)", (name, props_json))
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Product with this name already exists")
    
    return Response(status_code=201)

@app.get("/download")
async def download_product(name: str = Query(...)):
    with get_db_connection() as conn:
        row = conn.execute("SELECT properties FROM products WHERE name = ?", (name,)).fetchone()
        
    if row is None:
        raise HTTPException(status_code=400, detail="Product not found")
    
    # The spec says: "Download the entire current catalog... for a given product name as a data entry"
    # and the response schema is { "data": "string" }.
    # We return the JSON representation of the properties.
    return {"data": row["properties"]}

@app.post("/upload")
async def upload_product(payload: ProductUpload):
    try:
        # Validate that 'data' is a valid JSON string of properties
        properties = json.loads(payload.data)
        if not isinstance(properties, dict):
            raise ValueError()
        # Ensure all values are strings
        for v in properties.values():
            if not isinstance(v, str):
                raise ValueError()
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid upload query: data must be a JSON object of strings")

    with get_db_connection() as conn:
        # "once uploaded, it fully replaces any previous data for the product"
        conn.execute("INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)", 
                     (payload.name, payload.data))
        conn.commit()
    
    return {"message": "The product with the given name was updated."}

@app.get("/search")
async def search_products(query: str = Query(...)):
    if not query:
        raise HTTPException(status_code=400, detail="Invalid search query")

    results = []
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT name, properties FROM products")
        for row in cursor:
            name = row["name"]
            props = json.loads(row["properties"])
            
            # Match if query is in name or any of the property values
            match = (query.lower() in name.lower()) or any(query.lower() in str(v).lower() for v in props.values())
            
            if match:
                product_entry = {"name": name}
                product_entry.update(props)
                results.append(product_entry)
                
    return {"results": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)