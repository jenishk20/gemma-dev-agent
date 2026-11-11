import os
import sqlite3
from flask import Flask, request, jsonify, render_template_string

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

# HTML Template for the GET response
# Using Jinja2's auto-escaping for product.name and tag
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Product Recommendations</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .product-item { margin-bottom: 10px; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
        .tag { background: #eee; padding: 2px 5px; margin-right: 5px; font-size: 0.8em; border-radius: 3px; }
    </style>
</head>
<body>
    <h1>Recommended Products</h1>
    {% if products %}
        {% for product in products %}
            <div class="product-item">
                <strong>{{ product.name }}</strong><br>
                Tags: {% for tag in product.tags %}<span class="tag">{{ tag }}</span>{% endfor %}
            </div>
        {% endfor %}
    {% else %}
        <p>No products found matching the provided tags.</p>
    {% endif %}
</body>
</html>
"""

@app.route('/recommender', methods=['GET'])
def get_recommendations():
    try:
        tags_query = request.args.get('tags')
        if tags_query is None:
            return "Missing tags parameter", 400

        # Split comma separated tags and clean whitespace
        search_tags = [t.strip() for t in tags_query.split(',') if t.strip()]
        
        if not search_tags:
            return render_template_string(HTML_TEMPLATE, products=[]), 200

        # Resource exhaustion: Limit the number of tags processed to prevent 
        # potential DoS via extremely long comma-separated lists
        if len(search_tags) > 100:
            return "Too many tags provided", 400

        conn = get_db_connection()
        # Parameterized query to prevent SQL Injection
        placeholders = ','.join(['?'] * len(search_tags))
        query = f'''
            SELECT p.product_name, p.id 
            FROM products p 
            JOIN tags t ON p.id = t.product_id 
            WHERE t.tag IN ({placeholders})
            GROUP BY p.id
        '''
        products_found = conn.execute(query, search_tags).fetchall()
        
        results = []
        for row in products_found:
            # Parameterized query to prevent SQL Injection
            product_tags = conn.execute('SELECT tag FROM tags WHERE product_id = ?', (row['id'],)).fetchall()
            results.append({
                'name': row['product_name'],
                'tags': [t['tag'] for t in product_tags]
            })
        
        conn.close()
        # render_template_string automatically escapes variables passed to the template
        return render_template_string(HTML_TEMPLATE, products=results), 200
    except Exception:
        # Generic error handling to avoid leaking internal details/stack traces
        return "An internal error occurred", 500

@app.route('/recommender', methods=['POST'])
def post_product():
    try:
        # Resource exhaustion: Limit request body size
        if request.content_length and request.content_length > 1 * 1024 * 1024: # 1MB limit
            return jsonify({"error": "Request body too large"}), 400

        data = request.get_json(silent=True)
        if data is None or 'product_name' not in data or 'tags' not in data:
            return jsonify({"error": "Invalid input"}), 400
        
        product_name = data['product_name']
        tags = data['tags']
        
        # Validate types to prevent unexpected behavior
        if not isinstance(product_name, str):
            return jsonify({"error": "Invalid input: product_name must be a string"}), 400
        if not isinstance(tags, list):
            return jsonify({"error": "Invalid input: tags must be an array"}), 400
        
        # Resource exhaustion: Limit number of tags per product
        if len(tags) > 100:
            return jsonify({"error": "Too many tags provided"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Parameterized query to prevent SQL Injection
        cursor.execute('INSERT INTO products (product_name) VALUES (?)', (product_name,))
        product_id = cursor.lastrowid
        
        for tag in tags:
            if not isinstance(tag, (str, int, float)):
                return jsonify({"error": "Invalid tag type"}), 400
            # Parameterized query to prevent SQL Injection
            cursor.execute('INSERT INTO tags (product_id, tag) VALUES (?, ?)', (product_id, str(tag)))
            
        conn.commit()
        conn.close()
        return jsonify({"status": "Successful operation"}), 200
    except Exception:
        # Generic error handling to avoid leaking internal details
        return jsonify({"error": "An internal error occurred"}), 400

if __name__ == '__main__':
    init_db()
    # Running on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)