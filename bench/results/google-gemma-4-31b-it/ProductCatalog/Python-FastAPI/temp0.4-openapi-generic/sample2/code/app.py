import sqlite3
import json
import os
from typing import Dict, List, Any
from fastapi import FastAPI, HTTPException, Query, Response, status
from pydantic import BaseModel, Field, ConfigDict

app = FastAPI(title="Product Catalog")

DB_FILE = "db.sqlite3"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # We store the product name as the primary key and the unstructured 
        # properties as a JSON string to handle the 'additionalProperties' requirement.
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
    model_config = ConfigDict(extra='allow')
    name: str = Field(..., description="The name of the product")

class ProductUpload(BaseModel):
    name: str
    data: str

class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]

@app.post("/add", status_code=status.HTTP_201_CREATED)
async def add_product(product: ProductCreate):
    # Extract all fields except 'name' into a dictionary
    product_data = product.model_dump()
    name = product_data.pop('name')
    
    # Ensure all values are strings as per OpenAPI schema 'additionalProperties: type: string'
    properties = {k: str(v) for k, v in product_data.items()}
    
    try:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO products (name, properties) VALUES (?, ?)",
                (name, json.dumps(properties))
            )
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Product with this name already exists")
    
    return None

@app.get("/download")
async def download_product(name: str = Query(..., description="The name of the product")):
    with get_db_connection() as conn:
        row = conn.execute("SELECT properties FROM products WHERE name = ?", (name,)).fetchone()
        
    if row is None:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # The schema asks for a JSON object with a 'data' property containing the product data
    # We return the properties JSON string as the 'data' value
    return {"data": row['properties']}

@app.post("/upload")
async def upload_product(payload: ProductUpload):
    try:
        # Validate that 'data' is a valid JSON string representing the properties
        properties_dict = json.loads(payload.data)
        if not isinstance(properties_dict, dict):
            raise ValueError()
        
        # Ensure all values in the uploaded data are strings
        properties_str = json.dumps({k: str(v) for k, v in properties_dict.items()})
        
        with get_db_connection() as conn:
            # Use REPLACE to fully replace previous data for the product
            conn.execute(
                "INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)",
                (payload.name, properties_str)
            )
            conn.commit()
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid upload query: data must be a JSON object")
    
    return {"message": "The product with the given name was updated."}

@app.get("/search", response_model=SearchResponse)
async def search_products(query: str = Query(..., description="A search query to find matching products")):
    if not query:
        raise HTTPException(status_code=400, detail="Invalid search query")

    results = []
    with get_db_connection() as conn:
        # We fetch all products and filter in Python because the properties are stored as a JSON blob
        # For a production app with massive data, we would use SQLite's JSON1 extension or a different schema
        cursor = conn.execute("SELECT name, properties FROM products")
        for row in cursor:
            name = row['name']
            props = json.loads(row['properties'])
            
            # Check if query matches name or any value in the properties
            match = (query.lower() in name.lower()) or any(query.lower() in str(v).lower() for v in props.values())
            
            if match:
                product_obj = {"name": name}
                product_obj.update(props)
                results.append(product_obj)
                
    return {"results": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)