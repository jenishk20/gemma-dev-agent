import sqlite3
import os
from typing import List
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from jinja2 import Template
import uvicorn

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

# --- Models ---
class ProductCreate(BaseModel):
    product_name: str
    tags: List[str]

# --- App Initialization ---
app = FastAPI(title="Recommendation", version="1.0.11")
init_db()

# HTML Template for the GET response
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Recommended Products</title>
    <style>
        body { font-family: sans-serif; margin: 20px; }
        .product-item { margin-bottom: 10px; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
        .tag { background: #eee; padding: 2px 5px; margin-right: 5px; font-size: 0.8em; border-radius: 3px; }
    </style>
</head>
<body>
    <h1>Recommended Products</h1>
    {% if products %}
        {% for p in products %}
            <div class="product-item">
                <strong>{{ p.name }}</strong><br>
                Tags: {% for t in p.tags %}<span class="tag">{{ t }}</span>{% endfor %}
            </div>
        {% endfor %}
    {% else %}
        <p>No products found matching the provided tags.</p>
    {% endif %}
</body>
</html>
"""
jinja_template = Template(HTML_TEMPLATE)

@app.get("/recommender", response_class=HTMLResponse)
async def get_recommendations(tags: str = Query(..., description="Tags to search for separated by comma.")):
    search_tags = [t.strip() for t in tags.split(",") if t.strip()]
    if not search_tags:
        return jinja_template.render(products=[])

    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Find products that have at least one of the search tags
        # We use a JOIN and a WHERE IN clause
        placeholders = ','.join(['?'] * len(search_tags))
        query = f"""
            SELECT DISTINCT p.id, p.product_name 
            FROM products p 
            JOIN tags t ON p.id = t.product_id 
            WHERE t.tag IN ({placeholders})
        """
        cursor.execute(query, search_tags)
        product_rows = cursor.fetchall()
        
        results = []
        for row in product_rows:
            p_id = row['id']
            p_name = row['product_name']
            # Get all tags for this specific product to display them
            cursor.execute("SELECT tag FROM tags WHERE product_id = ?", (p_id,))
            p_tags = [t[0] for t in cursor.fetchall()]
            results.append({"name": p_name, "tags": p_tags})

    return jinja_template.render(products=results)

@app.post("/recommender")
async def post_product(product: ProductCreate):
    if not product.product_name:
        raise HTTPException(status_code=400, detail="Invalid input: product_name is required")
    
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            # Insert product
            cursor.execute("INSERT INTO products (product_name) VALUES (?)", (product.product_name,))
            product_id = cursor.lastrowid
            
            # Insert tags
            for tag in product.tags:
                cursor.execute("INSERT INTO tags (product_id, tag) VALUES (?, ?)", (product_id, tag))
            
            conn.commit()
        return {"message": "Successful operation"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")

if __name__ == "__main__":
    # Start server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)