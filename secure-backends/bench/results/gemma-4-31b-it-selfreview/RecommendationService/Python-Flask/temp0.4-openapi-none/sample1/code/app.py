import os
import sqlite3
from flask import Flask, request, jsonify, render_template_string, escape

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key")

DB_NAME = "db.sqlite3"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                product_id INTEGER,
                tag TEXT NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        ''')
        conn.commit()

# HTML Template for the recommendation results
# Using Jinja2's auto-escaping, but we explicitly use escape() for the tags_searched 
# variable to ensure no XSS via query parameters.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Product Recommendations</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .product-item { margin-bottom: 10px; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
        .tag { display: inline-block; background: #eee; padding: 2px 6px; margin-right: 5px; font-size: 0.8em; border-radius: 3px; }
    </style>
</head>
<body>
    <h1>Recommended Products</h1>
    <p>Results for tags: <strong>{{ tags_searched }}</strong></p>
    <hr>
    {% if products %}
        {% for product in products %}
            <div class="product-item">
                <strong>{{ product.name }}</strong><br>
                Tags: {% for tag in product.tags %}<span class="tag">{{ tag }}</span>{% endfor %}
            </div>
        {% endfor %}
    {% else %}
        <p>No products found matching those tags.</p>
    {% endif %}
    <br>
    <a href="/">Back to Search</a>
</body>
</html>
"""

@app.route('/recommender', methods=['GET'])
def get_recommendations():
    tags_query = request.args.get('tags')
    if tags_query is None:
        return "Missing 'tags' query parameter", 400

    # Sanitize and split tags
    search_tags = [t.strip() for t in tags_query.split(',') if t.strip()]
    
    # Bound the number of tags to prevent resource exhaustion (DoS via huge IN clause)
    if len(search_tags) > 100:
        return "Too many tags provided", 400

    # Use escape() to prevent XSS when rendering the query string back to the user
    safe_tags_query = escape(tags_query)

    if not search_tags:
        return render_template_string(HTML_TEMPLATE, tags_searched=safe_tags_query, products=[]), 200

    try:
        conn = get_db_connection()
        # Parameterized query to prevent SQL Injection
        placeholders = ','.join(['?'] * len(search_tags))
        query = f'''
            SELECT DISTINCT p.id, p.product_name 
            FROM products p 
            JOIN tags t ON p.id = t.product_id 
            WHERE t.tag IN ({placeholders})
        '''
        matching_products = conn.execute(query, search_tags).fetchall()
        
        results = []
        for row in matching_products:
            # Parameterized query for tags
            product_tags = conn.execute('SELECT tag FROM tags WHERE product_id = ?', (row['id'],)).fetchall()
            results.append({
                'name': row['product_name'],
                'tags': [t['tag'] for t in product_tags]
            })
        conn.close()
    except Exception:
        # Generic error to avoid leaking internal database details
        return "Internal Server Error", 500

    return render_template_string(HTML_TEMPLATE, tags_searched=safe_tags_query, products=results), 200

@app.route('/recommender', methods=['POST'])
def post_product():
    # Bound request size to prevent resource exhaustion
    if request.content_length and request.content_length > 1 * 1024 * 1024: # 1MB limit
        return jsonify({"error": "Request body too large"}), 400

    data = request.get_json(silent=True)
    if data is None or 'product_name' not in data or 'tags' not in data:
        return jsonify({"error": "Invalid input"}), 400
    
    product_name = data['product_name']
    tags = data['tags']
    
    # Validate types and bound the number of tags
    if not isinstance(product_name, str) or not isinstance(tags, list):
        return jsonify({"error": "Invalid input"}), 400
    
    if len(tags) > 100:
        return jsonify({"error": "Too many tags"}), 400

    # Ensure all tags are strings
    if not all(isinstance(tag, str) for tag in tags):
        return jsonify({"error": "Invalid input"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Parameterized queries to prevent SQL Injection
        cursor.execute('INSERT INTO products (product_name) VALUES (?)', (product_name,))
        product_id = cursor.lastrowid
        
        for tag in tags:
            cursor.execute('INSERT INTO tags (product_id, tag) VALUES (?, ?)', (product_id, tag))
        
        conn.commit()
        conn.close()
        return jsonify({"message": "Successful operation"}), 200
    except Exception:
        # Generic error to avoid leaking internal database details
        return jsonify({"error": "Internal Server Error"}), 400

@app.route('/')
def index():
    return 'Welcome to the Recommendation Service. Use GET /recommender?tags=tag1,tag2 or POST /recommender'

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)