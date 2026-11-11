import sqlite3
import os
from typing import List
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from jinja2 import Template, escape
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
    # Added constraints to prevent resource exhaustion (extremely large strings)
    product_name: str = Field(..., max_length=1000)
    tags: List[str] = Field(..., max_items=100)

# HTML Template for the recommendation results
# Jinja2 auto-escapes by default when using Template.render if configured, 
# but we will explicitly use the 'escape' filter or ensure the environment is safe.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
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
    <a href="/recommender?tags=">Back to search</a>
</body>
</html>
"""

@app.get("/recommender", response_class=HTMLResponse)
async def get_recommendations(tags: str = Query(..., description="Tags to search for separated by comma", max_length=2000)):
    # Split and clean tags
    search_tags = [t.strip() for t in tags.split(",") if t.strip()]
    
    if not search_tags:
        # The schema requires tags to be provided; if empty/whitespace, it's effectively invalid input
        return HTMLResponse("Please provide valid tags.", status_code=400)

    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Parameterized query to prevent SQL Injection
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
                # Parameterized query for tags
                cursor.execute("SELECT tag FROM tags WHERE product_id = ?", (row['id'],))
                product_tags = [t[0] for t in cursor.fetchall()]
                results.append({
                    "name": row['product_name'],
                    "tags": product_tags
                })

        # Using Jinja2 Template. Jinja2 automatically escapes variables passed to {{ }} 
        # provided we don't use the |safe filter.
        template = Template(HTML_TEMPLATE)
        return template.render(products=results)
    except Exception:
        # Generic error to avoid leaking internal database details
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/recommender")
async def post_product(product: ProductCreate):
    # Pydantic handles basic type validation and max_length/max_items constraints.
    # Ensure strings are not just whitespace.
    if not product.product_name.strip():
        raise HTTPException(status_code=400, detail="Invalid input: product_name cannot be empty")
    
    if not product.tags or any(not t.strip() for t in product.tags):
        raise HTTPException(status_code=400, detail="Invalid input: tags cannot be empty")

    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            # Parameterized query to prevent SQL Injection
            cursor.execute("INSERT INTO products (product_name) VALUES (?)", (product.product_name,))
            product_id = cursor.lastrowid
            
            # Clean tags and use executemany for efficiency and safety
            tag_data = [(product_id, tag.strip()) for tag in product.tags]
            cursor.executemany("INSERT INTO tags (product_id, tag) VALUES (?, ?)", tag_data)
            conn.commit()
        return {"message": "Successful operation"}
    except Exception:
        # Return 400 as per OpenAPI schema for invalid input/processing errors
        raise HTTPException(status_code=400, detail="Invalid input")

if __name__ == "__main__":
    # Port 5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)