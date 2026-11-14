import sqlite3
import uvicorn
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List
from jinja2 import Template, escape

# --- Database Setup ---
DB_PATH = "db.sqlite3"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Table for products
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL
            )
        """)
        # Table for tags (Many-to-Many relationship)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tag_name TEXT UNIQUE NOT NULL
            )
        """)
        # Junction table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS product_tags (
                product_id INTEGER,
                tag_id INTEGER,
                FOREIGN KEY(product_id) REFERENCES products(id),
                FOREIGN KEY(tag_id) REFERENCES tags(id),
                PRIMARY KEY(product_id, tag_id)
            )
        """)
        conn.commit()

init_db()

# --- Models ---
class ProductCreate(BaseModel):
    product_name: str
    tags: List[str]

# --- App Initialization ---
app = FastAPI(title="Recommendation")

# HTML Template for the GET response
# Using Jinja2's auto-escaping is standard, but we ensure variables are handled safely.
HTML_TEMPLATE = Template("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Product Recommendations</title>
    <style>
        body { font-family: sans-serif; margin: 20px; }
        .product-item { border-bottom: 1px solid #ccc; padding: 10px 0; }
        .tag { background: #eee; border-radius: 3px; padding: 2px 5px; margin-right: 5px; font-size: 0.8em; }
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
""")

@app.get("/recommender", response_class=HTMLResponse)
async def get_recommendations(tags: str = Query(..., description="Tags to search for separated by comma.")):
    # Resource Exhaustion: Limit the number of tags processed to prevent DoS via massive query strings
    raw_tags = tags.split(",")
    if len(raw_tags) > 100:
        raise HTTPException(status_code=400, detail="Too many tags provided")

    search_tags = [t.strip() for t in raw_tags if t.strip()]
    if not search_tags:
        return HTML_TEMPLATE.render(products=[])

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # SQL Injection Prevention: Using parameterized queries for the IN clause
            placeholders = ','.join(['?'] * len(search_tags))
            query = f"""
                SELECT DISTINCT p.id, p.product_name 
                FROM products p
                JOIN product_tags pt ON p.id = pt.product_id
                JOIN tags t ON pt.tag_id = t.id
                WHERE t.tag_name IN ({placeholders})
            """
            
            cursor.execute(query, search_tags)
            product_rows = cursor.fetchall()
            
            results = []
            for p_id, p_name in product_rows:
                cursor.execute("""
                    SELECT t.tag_name 
                    FROM tags t 
                    JOIN product_tags pt ON t.id = pt.tag_id 
                    WHERE pt.product_id = ?
                """, (p_id,))
                p_tags = [row[0] for row in cursor.fetchall()]
                
                # XSS Prevention: Explicitly escape content before passing to template 
                # (Though Jinja2 auto-escapes by default, we ensure the data is clean)
                results.append({
                    "name": escape(p_name), 
                    "tags": [escape(t) for t in p_tags]
                })

        return HTML_TEMPLATE.render(products=results)
    except Exception:
        # Error Handling: Prevent leaking internal database details
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/recommender")
async def post_product(product: ProductCreate):
    # Input Validation
    if not product.product_name or not product.product_name.strip():
        raise HTTPException(status_code=400, detail="Invalid input: product_name is required")
    
    # Resource Exhaustion: Limit number of tags per product
    if len(product.tags) > 50:
        raise HTTPException(status_code=400, detail="Too many tags provided")

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # SQL Injection Prevention: Parameterized queries
            cursor.execute("INSERT INTO products (product_name) VALUES (?)", (product.product_name,))
            product_id = cursor.lastrowid
            
            for tag_name in product.tags:
                tag_name = tag_name.strip()
                if not tag_name: 
                    continue
                
                # Limit tag length to prevent DB bloat/DoS
                if len(tag_name) > 100:
                    continue

                cursor.execute("INSERT OR IGNORE INTO tags (tag_name) VALUES (?)", (tag_name,))
                cursor.execute("SELECT id FROM tags WHERE tag_name = ?", (tag_name,))
                row = cursor.fetchone()
                if row:
                    tag_id = row[0]
                    cursor.execute("INSERT OR IGNORE INTO product_tags (product_id, tag_id) VALUES (?, ?)", (product_id, tag_id))
            
            conn.commit()
    except Exception:
        # Error Handling: Return documented 400 for invalid input/DB errors without leaking traces
        raise HTTPException(status_code=400, detail="Invalid input")

    return {"message": "Successful operation"}

if __name__ == "__main__":
    # Port 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)