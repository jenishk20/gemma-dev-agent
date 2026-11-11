import sqlite3
import os
from typing import List
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from jinja2 import Template
import uvicorn

# Database setup
DB_FILE = "db.sqlite3"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                product_id INTEGER,
                tag TEXT NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        """)
        conn.commit()

init_db()

app = FastAPI(title="Recommendation")

class ProductCreate(BaseModel):
    product_name: str
    tags: List[str]

# HTML Template for the recommendation results
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Product Recommendations</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .product-item { margin-bottom: 10px; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
        .tag { display: inline-block; background: #eee; padding: 2px 5px; margin-right: 5px; font-size: 0.8em; border-radius: 3px; }
    </style>
</head>
<body>
    <h1>Recommended Products</h1>
    {% if products %}
        {% for product in products %}
            <div class="product-item">
                <strong>{{ product.name }}</strong><br>
                {% for tag in product.tags %}
                    <span class="tag">{{ tag }}</span>
                {% endfor %}
            </div>
        {% endfor %}
    {% else %}
        <p>No products found matching the provided tags.</p>
    {% endif %}
    <hr>
    <a href="/">Back to search</a>
</body>
</html>
"""

@app.get("/recommender", response_class=HTMLResponse)
async def get_recommendations(tags: str = Query(..., description="Tags to search for separated by comma")):
    search_tags = [t.strip() for t in tags.split(",") if t.strip()]
    if not search_tags:
        return HTMLResponse("Please provide valid tags.", status_code=400)

    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Find products that have at least one of the search tags
        # Using a JOIN and WHERE IN clause
        placeholders = ','.join(['?'] * len(search_tags))
        query = f"""
            SELECT DISTINCT p.id, p.product_name 
            FROM products p 
            JOIN tags t ON p.id = t.product_id 
            WHERE t.tag IN ({placeholders})
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

    template = Template(HTML_TEMPLATE)
    return template.render(products=results)

@app.post("/recommender")
async def post_product(product: ProductCreate):
    if not product.product_name or not product.tags:
        raise HTTPException(status_code=400, detail="Invalid input: product_name and tags are required")

    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO products (product_name) VALUES (?)", (product.product_name,))
            product_id = cursor.lastrowid
            
            tag_data = [(product_id, tag) for tag in product.tags]
            cursor.executemany("INSERT INTO tags (product_id, tag) VALUES (?, ?)", tag_data)
            conn.commit()
        return {"message": "Successful operation"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)