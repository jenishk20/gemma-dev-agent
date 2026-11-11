import sqlite3
import json
import os
from typing import Dict, List, Any
from fastapi import FastAPI, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

app = FastAPI(title="Product Catalog")

DB_PATH = "db.sqlite3"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # We store the product name as a primary key.
        # The unstructured properties are stored as a JSON string in the 'properties' column.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                name TEXT PRIMARY KEY,
                properties TEXT
            )
        """)
        conn.commit()

@app.on_event("startup")
def startup():
    init_db()

class ProductCreate(BaseModel):
    name: str
    # Pydantic allows capturing extra fields via model_extra if configured, 
    # but for a simple API we can use a root validator or just accept a dict.
    # Since the schema specifies additionalProperties: string, we handle this in the route.

class ProductUpload(BaseModel):
    name: str
    data: str

@app.post("/add", status_code=status.HTTP_201_CREATED)
async def add_product(product: Dict[str, Any]):
    if not product or "name" not in product:
        raise HTTPException(status_code=400, detail="Invalid input: 'name' is required")
    
    name = product.pop("name")
    # Ensure all additional properties are strings as per schema
    for k, v in product.items():
        if not isinstance(v, str):
            raise HTTPException(status_code=400, detail=f"Property {k} must be a string")

    properties_json = json.dumps(product)
    
    try:
        with get_db_connection() as conn:
            conn.execute("INSERT INTO products (name, properties) VALUES (?, ?)", (name, properties_json))
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Product with this name already exists")
    
    return Response(status_code=status.HTTP_201_CREATED)

@app.get("/download")
async def download_product(name: str = Query(...)):
    with get_db_connection() as conn:
        row = conn.execute("SELECT properties FROM products WHERE name = ?", (name,)).fetchone()
        
    if row is None:
        raise HTTPException(status_code=400, detail="Product not found")
    
    # The schema asks for a JSON object with a 'data' field containing the product data string
    # The "data" should represent the product entry (name + properties)
    properties = json.loads(row['properties'])
    full_entry = {"name": name, **properties}
    
    return {"data": json.dumps(full_entry)}

@app.post("/upload")
async def upload_product(payload: ProductUpload):
    try:
        data_obj = json.loads(payload.data)
        if not isinstance(data_obj, dict) or "name" not in data_obj:
            raise ValueError("Invalid data format")
        
        # The upload must replace data for the product named in the payload.
        # The schema says "upload data for a product with the given name".
        # We extract the properties (everything except name) from the data string.
        name = payload.name
        properties = {k: v for k, v in data_obj.items() if k != "name"}
        
        # Validate that all properties are strings
        for v in properties.values():
            if not isinstance(v, str):
                raise ValueError("All properties must be strings")

        properties_json = json.dumps(properties)
        
        with get_db_connection() as conn:
            conn.execute("INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)", (name, properties_json))
            conn.commit()
            
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid upload query")
    
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
            properties = json.loads(row['properties'])
            
            # Match if query is in name or any property value
            match = (query in name) or any(query in str(v) for v in properties.values())
            
            if match:
                product_entry = {"name": name}
                product_entry.update(properties)
                results.append(product_entry)
                
    return {"results": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)