import sqlite3
import os
from typing import List
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from jinja2 import Template, escape
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
    # Bound input size to prevent resource exhaustion
    product_name: str = Field(..., max_length=1000)
    tags: List[str] = Field(..., max_length=100) # Max 100 tags

    # Validate individual tag length to prevent DB bloat/DoS
    def validate_tags(self):
        for tag in self.tags:
            if len(tag) > 100:
                raise ValueError("Tag too long")

# --- App Initialization ---
app = FastAPI(title="Recommendation", version="1.0.11")
init_db()

# HTML Template for the GET response
# Note: Jinja2 auto-escapes by default when using render, but we ensure 
# the template is structured to handle data safely.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
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
# Initialize template with autoescape=True to prevent XSS
jinja_template = Template(HTML_TEMPLATE)

@app.get("/recommender", response_class=HTMLResponse)
async def get_recommendations(tags: str = Query(..., description="Tags to search for separated by comma.", max_length=2000)):
    try:
        # Sanitize and split input
        search_tags = [t.strip() for t in tags.split(",") if t.strip()]
        if not search_tags:
            return jinja_template.render(products=[])

        # Limit the number of tags processed to prevent SQL query length issues/DoS
        search_tags = search_tags[:100]

        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Use parameterized query to prevent SQL Injection
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
                # Parameterized query for tags
                cursor.execute("SELECT tag FROM tags WHERE product_id = ?", (p_id,))
                p_tags = [t[0] for t in cursor.fetchall()]
                results.append({"name": p_name, "tags": p_tags})

        # Jinja2 render handles HTML escaping of p_name and p_tags
        return jinja_template.render(products=results)
    except Exception:
        # Generic error to avoid leaking internal details
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/recommender")
async def post_product(product: ProductCreate):
    # Validate tag lengths
    try:
        product.validate_tags()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not product.product_name.strip():
        raise HTTPException(status_code=400, detail="Invalid input: product_name is required")
    
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            # Use parameterized queries to prevent SQL Injection
            cursor.execute("INSERT INTO products (product_name) VALUES (?)", (product.product_name,))
            product_id = cursor.lastrowid
            
            for tag in product.tags:
                if tag.strip():
                    cursor.execute("INSERT INTO tags (product_id, tag) VALUES (?, ?)", (product_id, tag))
            
            conn.commit()
        return {"message": "Successful operation"}
    except Exception:
        # Return documented 400 for invalid input/DB errors without leaking stack traces
        raise HTTPException(status_code=400, detail="Invalid input")

if __name__ == "__main__":
    # Start server on 0.0.0.0:5000
    uvicorn.run(app, host="0.0.0.0", port=5000)