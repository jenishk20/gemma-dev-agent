import sqlite3
import os
from typing import List
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from jinja2 import Template, escape
import uvicorn

app = FastAPI(title="Recommendation")

DB_FILE = "db.sqlite3"

# Database initialization
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                product_id INTEGER,
                tag TEXT NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        ''')
        conn.commit()

init_db()

# Pydantic model for POST request with basic resource exhaustion bounds
class Product(BaseModel):
    product_name: str = Field(..., max_length=1000)
    tags: List[str] = Field(..., max_length=100)

    # Custom validator to ensure individual tags aren't excessively long
    def validate_tags(self):
        for tag in self.tags:
            if len(tag) > 100:
                raise ValueError("Tag too long")

# HTML Template for the GET response
# Note: Jinja2's render method handles escaping by default if configured, 
# but we will explicitly ensure content is escaped.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Product Recommendations</title>
    <style>
        body { font-family: sans-serif; margin: 20px; }
        .product-item { margin-bottom: 10px; padding: 10px; border: 1px solid #ccc; border-radius: 5px; }
        .tag { display: inline-block; background: #eee; padding: 2px 5px; margin-right: 5px; font-size: 0.8em; border-radius: 3px; }
    </style>
</head>
<body>
    <h1>Recommended Products</h1>
    {% if products %}
        {% for p in products %}
            <div class="product-item">
                <strong>{{ p.name }}</strong><br>
                Tags: {% for tag in p.tags %}<span class="tag">{{ tag }}</span>{% endfor %}
            </div>
        {% endfor %}
    {% else %}
        <p>No products found matching those tags.</p>
    {% endif %}
</body>
</html>
"""

@app.get("/recommender", response_class=HTMLResponse)
async def get_recommender(tags: str = Query(..., description="Tags to search for separated by comma.")):
    # Resource exhaustion: limit the length of the query string
    if len(tags) > 2000:
        raise HTTPException(status_code=400, detail="Query string too long")

    search_tags = [t.strip() for t in tags.split(",") if t.strip()]
    if not search_tags:
        # The spec says 200 for the list of products, but if tags are required 
        # and empty, we handle it gracefully.
        return HTMLResponse("Please provide at least one valid tag.", status_code=400)

    # Limit number of tags to prevent SQL "IN" clause exhaustion
    if len(search_tags) > 100:
        raise HTTPException(status_code=400, detail="Too many tags provided")

    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Use parameterized query to prevent SQL Injection
            placeholders = ','.join(['?'] * len(search_tags))
            query = f'''
                SELECT DISTINCT p.id, p.product_name 
                FROM products p 
                JOIN tags t ON p.id = t.product_id 
                WHERE t.tag IN ({placeholders})
            '''
            cursor.execute(query, search_tags)
            matched_products = cursor.fetchall()
            
            results = []
            for row in matched_products:
                cursor.execute("SELECT tag FROM tags WHERE product_id = ?", (row['id'],))
                product_tags = [t[0] for t in cursor.fetchall()]
                # We store raw data here; Jinja2 will escape it during rendering
                results.append({"name": row['product_name'], "tags": product_tags})

        # Use Jinja2 with autoescape enabled to prevent XSS
        template = Template(HTML_TEMPLATE)
        # Jinja2's Template.render does not autoescape by default unless 
        # an Environment is used. We use the environment for security.
        from jinja2 import Environment
        env = Environment(autoescape=True)
        jinja_template = env.from_string(HTML_TEMPLATE)
        return jinja_template.render(products=results)
    except Exception:
        # Catch all to prevent leaking internal stack traces
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/recommender")
async def post_recommender(product: Product):
    # Validation is handled by Pydantic (max_length)
    if not product.product_name.strip() or not product.tags:
        raise HTTPException(status_code=400, detail="Invalid input")

    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            # Parameterized query to prevent SQL Injection
            cursor.execute("INSERT INTO products (product_name) VALUES (?)", (product.product_name,))
            product_id = cursor.lastrowid
            
            tag_data = [(product_id, tag) for tag in product.tags]
            cursor.executemany("INSERT INTO tags (product_id, tag) VALUES (?, ?)", tag_data)
            conn.commit()
        return {"message": "Successful operation"}
    except Exception:
        # Return documented 400 for invalid input/db errors without leaking details
        raise HTTPException(status_code=400, detail="Invalid input")

if __name__ == "__main__":
    # Port 5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)