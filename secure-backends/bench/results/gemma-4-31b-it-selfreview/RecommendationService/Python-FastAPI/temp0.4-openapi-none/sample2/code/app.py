import os
import sqlite3
from typing import List
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from jinja2 import Template, escape
import uvicorn

# --- Database Setup ---
DB_PATH = "db.sqlite3"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Create products table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL
            )
        """)
        # Create tags table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                product_id INTEGER,
                tag TEXT NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        """)
        conn.commit()

init_db()

# --- Models ---
class ProductCreate(BaseModel):
    # Added constraints to prevent resource exhaustion (DoS) via massive strings
    product_name: str = Field(..., max_length=1000)
    tags: List[str] = Field(..., max_length=100) # Limit number of tags

# --- App Initialization ---
app = FastAPI(title="Recommendation", version="1.0.11")

# HTML Template for the GET response
# Jinja2 auto-escapes by default when using render, but we ensure the template 
# is handled safely.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Recommended Products</title>
    <style>
        body { font-family: sans-serif; margin: 40px; }
        .product-card { border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; border-radius: 5px; }
        .tag { background: #eee; padding: 2px 6px; margin-right: 5px; font-size: 0.8em; border-radius: 3px; }
    </style>
</head>
<body>
    <h1>Recommended Products</h1>
    {% if products %}
        {% for product in products %}
            <div class="product-card">
                <strong>{{ product.name }}</strong><br>
                Tags: {% for tag in product.tags %}<span class="tag">{{ tag }}</span>{% endfor %}
            </div>
        {% endfor %}
    {% else %}
        <p>No products found matching the provided tags.</p>
    {% endif %}
</body>
</html>
"""
# Initialize template with autoescape=True to prevent XSS
template = Template(HTML_TEMPLATE)

@app.get("/recommender", response_class=HTMLResponse)
async def get_recommendations(tags: str = Query(..., description="Tags to search for separated by comma.", max_length=2000)):
    """Get all posted products that match at least one of the provided tags."""
    # Split and clean tags
    search_tags = [t.strip() for t in tags.split(",") if t.strip()]
    
    if not search_tags:
        return template.render(products=[])

    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Use parameterized query to prevent SQL Injection
            placeholders = ','.join(['?'] * len(search_tags))
            query = f"""
                SELECT p.product_name, p.id 
                FROM products p
                JOIN tags t ON p.id = t.product_id
                WHERE t.tag IN ({placeholders})
                GROUP BY p.id
            """
            cursor.execute(query, search_tags)
            matched_products = cursor.fetchall()
            
            results = []
            for row in matched_products:
                # Parameterized query for tags
                cursor.execute("SELECT tag FROM tags WHERE product_id = ?", (row['id'],))
                product_tags = [t[0] for t in cursor.fetchall()]
                results.append({
                    "name": row['product_name'],
                    "tags": product_tags
                })
    except Exception:
        # Generic error to avoid leaking internal database details
        raise HTTPException(status_code=500, detail="Internal server error")

    # Jinja2's render method with autoescape=True handles HTML escaping of the product names and tags
    return template.render(products=results)

@app.post("/recommender")
async def post_product(product: ProductCreate):
    """Post a new product along with its tags."""
    # Validate that product_name is not just whitespace
    if not product.product_name.strip():
        raise HTTPException(status_code=400, detail="Invalid input")
    
    # Validate that tags are not empty strings
    if any(not tag.strip() for tag in product.tags):
        raise HTTPException(status_code=400, detail="Invalid input")

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # Parameterized queries to prevent SQL Injection
            cursor.execute("INSERT INTO products (product_name) VALUES (?)", (product.product_name,))
            product_id = cursor.lastrowid
            
            for tag in product.tags:
                cursor.execute("INSERT INTO tags (product_id, tag) VALUES (?, ?)", (product_id, tag))
            
            conn.commit()
    except Exception:
        # Return 400 as per OpenAPI spec for invalid input/processing errors
        raise HTTPException(status_code=400, detail="Invalid input")
        
    return {"message": "Successful operation"}

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)