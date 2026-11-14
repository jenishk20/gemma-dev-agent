import sqlite3
import os
from typing import List
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from jinja2 import Template

app = FastAPI(title="Recommendation")

DB_PATH = "db.sqlite3"

# Pydantic model for POST request
class Product(BaseModel):
    product_name: str
    tags: List[str]

# Database initialization
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Create products table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
        """)
        # Create tags table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                product_id INTEGER,
                tag TEXT NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)
        conn.commit()

init_db()

# HTML Template for the GET response
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Product Recommendations</title>
    <style>
        body { font-family: sans-serif; margin: 40px; line-height: 1.6; }
        .product-card { border: 1px solid #ddd; padding: 10px; margin-bottom: 10px; border-radius: 5px; }
        .tag { background: #eee; padding: 2px 6px; margin-right: 5px; font-size: 0.8em; border-radius: 3px; }
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
        <p>No products found matching those tags.</p>
    {% endif %}
</body>
</html>
"""
jinja_template = Template(HTML_TEMPLATE)

@app.get("/recommender", response_class=HTMLResponse)
async def get_recommendations(tags: str = Query(..., description="Tags to search for separated by comma.")):
    # Split tags by comma and strip whitespace
    search_tags = [t.strip() for t in tags.split(",") if t.strip()]
    
    if not search_tags:
        return jinja_template.render(products=[])

    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Use parameterized query to prevent SQL injection
            # We find all products that have at least one of the provided tags
            placeholders = ','.join(['?'] * len(search_tags))
            query = f"""
                SELECT p.id, p.name 
                FROM products p 
                JOIN tags t ON p.id = t.product_id 
                WHERE t.tag IN ({placeholders}) 
                GROUP BY p.id
            """
            cursor.execute(query, search_tags)
            product_rows = cursor.fetchall()
            
            results = []
            for row in product_rows:
                # Fetch all tags for this specific product to display them
                cursor.execute("SELECT tag FROM tags WHERE product_id = ?", (row['id'],))
                product_tags = [t[0] for t in cursor.fetchall()]
                results.append({"name": row['name'], "tags": product_tags})
                
            return jinja_template.render(products=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/recommender")
async def post_product(product: Product):
    if not product.product_name or not product.tags:
        raise HTTPException(status_code=400, detail="Invalid input: product_name and tags are required.")

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # Insert product
            cursor.execute("INSERT INTO products (name) VALUES (?)", (product.product_name,))
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
    uvicorn.run(app, host="0.0.0.0", port=5000)