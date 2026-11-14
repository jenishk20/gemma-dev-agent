import sqlite3
import os
from typing import List
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from jinja2 import Template

# --- Configuration ---
DB_FILE = "db.sqlite3"
PORT = 5000
HOST = "0.0.0.0"

app = FastAPI(title="Recommendation")

# --- Database Setup ---
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # Create products table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL
            )
        """)
        # Create tags table
        conn.execute("""
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
    product_name: str
    tags: List[str]

# --- HTML Template ---
# Using a simple Jinja2 template for the HTML response
HTML_TEMPLATE = Template("""
<!DOCTYPE html>
<html>
<head>
    <title>Product Recommendations</title>
    <style>
        body { font-family: sans-serif; margin: 40px; line-height: 1.6; }
        .product-card { border: 1px solid #ddd; padding: 10px; margin-bottom: 10px; border-radius: 5px; }
        .tag { background: #e0e0e0; padding: 2px 6px; border-radius: 3px; font-size: 0.8em; margin-right: 5px; }
        h1 { color: #333; }
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
    <hr>
    <p><small>Search via query parameter: <code>?tags=tag1,tag2</code></small></p>
</body>
</html>
""")

# --- Routes ---

@app.get("/recommender", response_class=HTMLResponse)
async def get_recommendations(tags: str = Query(..., description="Tags to search for separated by comma.")):
    """Get all posted products that match at least one of the provided tags."""
    if not tags:
        return HTML_TEMPLATE.render(products=[])

    # Split tags and clean whitespace
    search_tags = [t.strip() for t in tags.split(",") if t.strip()]
    
    if not search_tags:
        return HTML_TEMPLATE.render(products=[])

    try:
        with get_db_connection() as conn:
            # Find products that have at least one of the requested tags
            # Using parameterized query to prevent SQL Injection
            placeholders = ','.join(['?'] * len(search_tags))
            query = f"""
                SELECT DISTINCT p.id, p.product_name 
                FROM products p
                JOIN tags t ON p.id = t.product_id
                WHERE t.tag IN ({placeholders})
            """
            cursor = conn.execute(query, search_tags)
            matched_products = cursor.fetchall()

            results = []
            for row in matched_products:
                # Fetch all tags for each matched product to display them
                tag_cursor = conn.execute("SELECT tag FROM tags WHERE product_id = ?", (row['id'],))
                product_tags = [t['tag'] for t in tag_cursor.fetchall()]
                results.append({
                    "name": row['product_name'],
                    "tags": product_tags
                })
            
            return HTML_TEMPLATE.render(products=results)
    except Exception as e:
        # Log error here in production
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/recommender")
async def post_product(product: ProductCreate):
    """Post a new product along with its tags."""
    if not product.product_name:
        raise HTTPException(status_code=400, detail="Product name is required")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Insert product
            cursor.execute("INSERT INTO products (product_name) VALUES (?)", (product.product_name,))
            product_id = cursor.lastrowid
            
            # Insert tags
            tag_data = [(product_id, tag.strip()) for tag in product.tags if tag.strip()]
            if tag_data:
                cursor.executemany("INSERT INTO tags (product_id, tag) VALUES (?, ?)", tag_data)
            
            conn.commit()
            return {"message": "Successful operation"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid input or database error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host=HOST, port=PORT)