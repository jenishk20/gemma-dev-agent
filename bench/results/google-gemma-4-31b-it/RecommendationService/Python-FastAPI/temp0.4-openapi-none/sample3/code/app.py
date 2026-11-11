import sqlite3
import uvicorn
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List
from jinja2 import Template

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
HTML_TEMPLATE = Template("""
<!DOCTYPE html>
<html>
<head>
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
    search_tags = [t.strip() for t in tags.split(",") if t.strip()]
    if not search_tags:
        return HTML_TEMPLATE.render(products=[])

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Find products that have at least one of the requested tags
        # We join products -> product_tags -> tags
        query = """
            SELECT DISTINCT p.id, p.product_name 
            FROM products p
            JOIN product_tags pt ON p.id = pt.product_id
            JOIN tags t ON pt.tag_id = t.id
            WHERE t.tag_name IN ({placeholder})
        """.format(placeholder=','.join(['?'] * len(search_tags)))
        
        cursor.execute(query, search_tags)
        product_rows = cursor.fetchall()
        
        results = []
        for p_id, p_name in product_rows:
            # Fetch all tags for this specific product to display them
            cursor.execute("""
                SELECT t.tag_name 
                FROM tags t 
                JOIN product_tags pt ON t.id = pt.tag_id 
                WHERE pt.product_id = ?
            """, (p_id,))
            p_tags = [row[0] for row in cursor.fetchall()]
            results.append({"name": p_name, "tags": p_tags})

    return HTML_TEMPLATE.render(products=results)

@app.post("/recommender")
async def post_product(product: ProductCreate):
    if not product.product_name:
        raise HTTPException(status_code=400, detail="Invalid input: product_name is required")

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Insert product
            cursor.execute("INSERT INTO products (product_name) VALUES (?)", (product.product_name,))
            product_id = cursor.lastrowid
            
            # Insert tags and link them
            for tag_name in product.tags:
                tag_name = tag_name.strip()
                if not tag_name: continue
                
                cursor.execute("INSERT OR IGNORE INTO tags (tag_name) VALUES (?)", (tag_name,))
                cursor.execute("SELECT id FROM tags WHERE tag_name = ?", (tag_name,))
                tag_id = cursor.fetchone()[0]
                
                cursor.execute("INSERT OR IGNORE INTO product_tags (product_id, tag_id) VALUES (?, ?)", (product_id, tag_id))
            
            conn.commit()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")

    return {"message": "Successful operation"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)