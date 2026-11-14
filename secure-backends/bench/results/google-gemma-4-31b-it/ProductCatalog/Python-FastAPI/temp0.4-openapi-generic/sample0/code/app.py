import os
import json
import sqlite3
from typing import Dict, List, Any
from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, Field

app = FastAPI(title="Product Catalog")
DB_PATH = "db.sqlite3"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
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

@app.on_event("startup")
def startup():
    init_db()

class ProductAdd(BaseModel):
    name: str
    # Pydantic allows capturing additional fields via model_extra if configured,
    # but for simplicity and strict adherence to the schema, we use a Dict.
    # We will handle the "additionalProperties" by treating the input as a dict.
    
    class Config:
        extra = "allow"

class ProductUpload(BaseModel):
    name: str
    data: str

@app.post("/add", status_code=201)
async def add_product(product: Dict[str, Any]):
    if "name" not in product:
        raise HTTPException(status_code=400, detail="Missing required field: name")
    
    name = product["name"]
    # Extract all properties except 'name' to store as JSON
    properties = {k: v for k, v in product.items() if k != "name"}
    
    try:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO products (name, properties) VALUES (?, ?)",
                (name, json.dumps(properties))
            )
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Product with this name already exists")
    
    return Response(status_code=201)

@app.get("/download")
async def download_product(name: str = Query(..., description="The name of the product")):
    with get_db_connection() as conn:
        row = conn.execute("SELECT properties FROM products WHERE name = ?", (name,)).fetchone()
        
    if row is None:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # The schema asks for the data as a string in a JSON object
    return {"data": row["properties"]}

@app.post("/upload")
async def upload_product(payload: ProductUpload):
    try:
        # Validate that data is a valid JSON string representing the properties
        properties_dict = json.loads(payload.data)
        if not isinstance(properties_dict, dict):
            raise ValueError()
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid upload query: data must be a JSON string")

    with get_db_connection() as conn:
        cursor = conn.execute("UPDATE products SET properties = ? WHERE name = ?", (payload.data, payload.name))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=400, detail="Product not found in catalog")
            
    return {"message": "The product with the given name was updated."}

@app.get("/search")
async def search_products(query: str = Query(..., description="Search query")):
    results = []
    with get_db_connection() as conn:
        # Fetch all products and filter in Python to handle unstructured JSON search
        rows = conn.execute("SELECT name, properties FROM products").fetchall()
        
    for row in rows:
        name = row["name"]
        props = json.loads(row["properties"])
        
        # Check if query matches name or any value in the properties
        match = False
        if query.lower() in name.lower():
            match = True
        else:
            for val in props.values():
                if isinstance(val, str) and query.lower() in val.lower():
                    match = True
                    break
        
        if match:
            product_obj = {"name": name}
            product_obj.update(props)
            results.append(product_obj)
            
    return {"results": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)