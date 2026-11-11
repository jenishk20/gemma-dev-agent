import os
import json
import sqlite3
from typing import Dict, List, Any
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
        # We store the product name as the primary key and the rest of the 
        # unstructured properties as a JSON string in a 'properties' column.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                name TEXT PRIMARY KEY,
                properties TEXT
            )
        """)
        conn.commit()

init_db()

class ProductCreate(BaseModel):
    name: str
    # Use extra='allow' to capture additionalProperties from the OpenAPI spec
    model_config = {"extra": "allow"}

class ProductUpload(BaseModel):
    name: str
    data: str

class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]

@app.post("/add", status_code=201)
async def add_product(product: ProductCreate):
    # Extract all fields except 'name' into a dictionary
    data = product.model_dump()
    name = data.pop("name")
    
    # Ensure all values are strings as per OpenAPI schema 'additionalProperties: type: string'
    properties = {k: str(v) for k, v in data.items()}
    props_json = json.dumps(properties)

    try:
        with get_db_connection() as conn:
            conn.execute("INSERT INTO products (name, properties) VALUES (?, ?)", (name, props_json))
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
    
    # The schema requires a response object with a 'data' string property
    # The data string should be the representation of the product (name + properties)
    props = json.loads(row["properties"])
    full_product = {"name": name, **props}
    return {"data": json.dumps(full_product)}

@app.post("/upload")
async def upload_product(payload: ProductUpload):
    try:
        product_data = json.loads(payload.data)
        if not isinstance(product_data, dict) or "name" not in product_data:
            raise ValueError("Invalid data format")
        
        # The upload must replace data for the product named in the payload
        # We validate that the name in the JSON data matches the name in the request body
        if product_data["name"] != payload.name:
            raise ValueError("Name mismatch between payload and data")

        name = product_data.pop("name")
        properties = {k: str(v) for k, v in product_data.items()}
        props_json = json.dumps(properties)

        with get_db_connection() as conn:
            conn.execute("INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)", (name, props_json))
            conn.commit()
            
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid upload query")

    return {"message": "The product with the given name was updated."}

@app.get("/search")
async def search_products(query: str = Query(...)):
    results = []
    with get_db_connection() as conn:
        rows = conn.execute("SELECT name, properties FROM products").fetchall()
        
    for row in rows:
        name = row["name"]
        props = json.loads(row["properties"])
        
        # Search in name or any of the property values
        match = (query.lower() in name.lower()) or any(query.lower() in str(v).lower() for v in props.values())
        
        if match:
            product_obj = {"name": name, **props}
            results.append(product_obj)

    return {"results": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)