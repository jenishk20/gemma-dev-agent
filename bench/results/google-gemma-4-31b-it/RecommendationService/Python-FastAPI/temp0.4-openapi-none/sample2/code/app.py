import os
import sqlite3
from typing import List
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from jinja2 import Template
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
    product_name: str
    tags: List[str]

# --- App Initialization ---
app = FastAPI(title="Recommendation", version="1.0.11")

# HTML Template for the GET response
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
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
template = Template(HTML_TEMPLATE)

@app.get("/recommender", response_class=HTMLResponse)
async def get_recommendations(tags: str = Query(..., description="Tags to search for separated by comma.")):
    """Get all posted products that match at least one of the provided tags."""
    search_tags = [t.strip() for t in tags.split(",") if t.strip()]
    
    if not search_tags:
        return template.render(products=[])

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Find products that have at least one of the tags
        # We join products and tags, filter by the list of tags, and group by product
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
            # Fetch all tags for this specific product to display them
            cursor.execute("SELECT tag FROM tags WHERE product_id = ?", (row['id'],))
            product_tags = [t[0] for t in cursor.fetchall()]
            results.append({
                "name": row['product_name'],
                "tags": product_tags
            })

    return template.render(products=results)

@app.post("/recommender")
async def post_product(product: ProductCreate):
    """Post a new product along with its tags."""
    if not product.product_name:
        raise HTTPException(status_code=400, detail="Invalid input: product_name is required")
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # Insert product
            cursor.execute("INSERT INTO products (product_name) VALUES (?)", (product.product_name,))
            product_id = cursor.lastrowid
            
            # Insert tags
            for tag in product.tags:
                cursor.execute("INSERT INTO tags (product_id, tag) VALUES (?, ?)", (product_id, tag))
            
            conn.commit()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    return {"message": "Successful operation"}

if __name__ == "__main__":
    # Start the server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)