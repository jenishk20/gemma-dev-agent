import sqlite3
import os
from typing import List
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from jinja2 import Template

# --- Configuration & Models ---
DB_PATH = "db.sqlite3"

class Product(BaseModel):
    product_name: str
    tags: List[str]

# --- Database Logic ---
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                product_id INTEGER,
                tag TEXT NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        """)
        conn.commit()

# --- HTML Template ---
HTML_TEMPLATE = Template("""
<!DOCTYPE html>
<html>
<head>
    <title>Product Recommendations</title>
    <style>
        body { font-family: sans-serif; margin: 40px; line-height: 1.6; }
        .product-item { border: 1px solid #ddd; padding: 10px; margin-bottom: 10px; border-radius: 5px; }
        .tag { background: #e0e0e0; padding: 2px 6px; border-radius: 3px; font-size: 0.8em; margin-right: 5px; }
        h1 { color: #333; }
    </style>
</head>
<body>
    <h1>Recommended Products</h1>
    {% if products %}
        {% for p in products %}
            <div class="product-item">
                <strong>{{ p.name }}</strong><br>
                {% for tag in p.tags %}
                    <span class="tag">{{ tag }}</span>
                {% endfor %}
            </div>
        {% endfor %}
    {% else %}
        <p>No products found matching those tags.</p>
    {% endif %}
    <hr>
    <p><small>Search by adding <code>?tags=tag1,tag2</code> to the URL</small></p>
</body>
</html>
""")

# --- App Initialization ---
app = FastAPI(title="Recommendation")

@app.on_event("startup")
async def startup_event():
    init_db()

# --- Routes ---

@app.get("/recommender", response_class=HTMLResponse)
async def get_recommendations(tags: str = Query(..., description="Tags to search for separated by comma.")):
    """Get all posted products that match at least one of the provided tags."""
    search_tags = [t.strip() for t in tags.split(",") if t.strip()]
    
    if not search_tags:
        return HTML_TEMPLATE.render(products=[])

    try:
        with get_db_connection() as conn:
            # Find products that have at least one of the requested tags
            # Using a parameterized query to prevent SQL injection
            placeholders = ','.join(['?'] * len(search_tags))
            query = f"""
                SELECT p.name, GROUP_CONCAT(t.tag, ',') as product_tags
                FROM products p
                JOIN tags t ON p.id = t.product_id
                WHERE p.id IN (
                    SELECT product_id FROM tags WHERE tag IN ({placeholders})
                )
                GROUP BY p.id
            """
            cursor = conn.execute(query, search_tags)
            rows = cursor.fetchall()
            
            products = []
            for row in rows:
                products.append({
                    "name": row["name"],
                    "tags": row["product_tags"].split(",")
                })
            
            return HTML_TEMPLATE.render(products=products)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/recommender")
async def post_product(product: Product):
    """Post a new product along with its tags."""
    if not product.product_name:
        raise HTTPException(status_code=400, detail="Product name is required")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Insert product
            cursor.execute("INSERT INTO products (name) VALUES (?)", (product.product_name,))
            product_id = cursor.lastrowid
            
            # Insert tags
            tag_data = [(product_id, tag.strip()) for tag in product.tags if tag.strip()]
            cursor.executemany("INSERT INTO tags (product_id, tag) VALUES (?, ?)", tag_data)
            
            conn.commit()
            return {"message": "Successful operation"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid input or database error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    # Start the server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)