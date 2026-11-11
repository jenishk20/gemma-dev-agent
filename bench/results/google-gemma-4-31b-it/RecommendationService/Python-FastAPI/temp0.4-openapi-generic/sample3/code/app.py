import sqlite3
import os
from typing import List
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from jinja2 import Template

# --- Database Setup ---
DB_FILE = "db.sqlite3"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
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

# HTML Template for the recommendation list
HTML_TEMPLATE = Template("""
<!DOCTYPE html>
<html>
<head>
    <title>Product Recommendations</title>
    <style>
        body { font-family: sans-serif; margin: 40px; line-height: 1.6; }
        .product-item { border: 1px solid #ddd; padding: 10px; margin-bottom: 10px; border-radius: 5px; }
        .product-name { font-weight: bold; font-size: 1.2em; }
        .tags { color: #666; font-style: italic; }
    </style>
</head>
<body>
    <h1>Recommended Products</h1>
    {% if products %}
        {% for p in products %}
            <div class="product-item">
                <div class="product-name">{{ p.name }}</div>
                <div class="tags">Tags: {{ p.tags }}</div>
            </div>
        {% endfor %}
    {% else %}
        <p>No products found matching the provided tags.</p>
    {% endif %}
    <br>
    <a href="/">Back to search</a>
</body>
</html>
""")

@app.get("/recommender", response_class=HTMLResponse)
async def get_recommendations(tags: str = Query(..., description="Tags to search for separated by comma.")):
    """Get all posted products that match at least one of the provided tags."""
    search_tags = [t.strip() for t in tags.split(",") if t.strip()]
    
    if not search_tags:
        return HTML_TEMPLATE.render(products=[])

    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Use parameterized query to prevent SQL injection
            # We join products and tags, filtering for any tag in the provided list
            placeholders = ','.join(['?'] * len(search_tags))
            query = f"""
                SELECT DISTINCT p.product_name 
                FROM products p 
                JOIN tags t ON p.id = t.product_id 
                WHERE t.tag IN ({placeholders})
            """
            cursor.execute(query, search_tags)
            rows = cursor.fetchall()
            
            # For each product, we need to fetch all its tags to display them
            results = []
            for row in rows:
                p_name = row['product_name']
                # Get all tags for this specific product
                cursor.execute("SELECT tag FROM tags JOIN products ON tags.product_id = products.id WHERE products.product_name = ?", (p_name,))
                p_tags = [r[0] for r in cursor.fetchall()]
                results.append({"name": p_name, "tags": ", ".join(p_tags)})
                
            return HTML_TEMPLATE.render(products=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/recommender")
async def create_product(product: ProductCreate):
    """Post a new product along with its tags."""
    if not product.product_name or not product.tags:
        raise HTTPException(status_code=400, detail="Invalid input: product_name and tags are required.")

    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            # Insert product
            cursor.execute("INSERT INTO products (product_name) VALUES (?)", (product.product_name,))
            product_id = cursor.lastrowid
            
            # Insert tags
            tag_data = [(product_id, tag) for tag in product.tags]
            cursor.executemany("INSERT INTO tags (product_id, tag) VALUES (?, ?)", tag_data)
            conn.commit()
            
        return {"message": "Successful operation"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)