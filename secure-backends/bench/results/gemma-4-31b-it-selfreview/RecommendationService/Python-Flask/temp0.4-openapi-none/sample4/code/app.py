import os
import sqlite3
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
# Ensure secret key is handled securely from environment
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key_for_dev_only")

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

# HTML Template for the GET response. 
# Jinja2 automatically escapes variables ({{ product }}), preventing XSS.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Product Recommendations</title></head>
<body>
    <h1>Recommended Products</h1>
    <ul>
    {% for product in products %}
        <li>{{ product }}</li>
    {% endfor %}
    </ul>
    {% if not products %}
        <p>No products found matching those tags.</p>
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

        # Split tags by comma and strip whitespace
        search_tags = [t.strip() for t in tags_query.split(',') if t.strip()]
        
        if not search_tags:
            return render_template_string(HTML_TEMPLATE, products=[]), 200

        # Limit the number of tags to prevent potential DoS via extremely large IN clauses
        if len(search_tags) > 1000:
            return "Too many tags provided", 400

        conn = get_db_connection()
        # Use parameterized query to prevent SQL Injection
        placeholders = ', '.join(['?'] * len(search_tags))
        query = f'''
            SELECT DISTINCT p.product_name 
            FROM products p 
            JOIN tags t ON p.id = t.product_id 
            WHERE t.tag IN ({placeholders})
        '''
        cursor = conn.execute(query, search_tags)
        products = [row['product_name'] for row in cursor.fetchall()]
        conn.close()

        return render_template_string(HTML_TEMPLATE, products=products), 200
    except Exception:
        # Generic error to avoid leaking internal stack traces
        return "An internal error occurred", 500

@app.route('/recommender', methods=['POST'])
def post_product():
    try:
        # Bound request size check (Flask does this via MAX_CONTENT_LENGTH if configured, 
        # but we check for JSON validity here)
        data = request.get_json(silent=True)
        if data is None or 'product_name' not in data or 'tags' not in data:
            return jsonify({"error": "Invalid input"}), 400
        
        product_name = data['product_name']
        tags = data['tags']

        # Validate types to prevent unexpected behavior or crashes
        if not isinstance(product_name, str):
            return jsonify({"error": "Invalid input"}), 400
        
        if not isinstance(tags, list):
            return jsonify({"error": "Invalid input"}), 400

        # Limit the number of tags per product to prevent resource exhaustion
        if len(tags) > 100:
            return jsonify({"error": "Too many tags"}), 400

        # Ensure all tags are strings
        if not all(isinstance(tag, str) for tag in tags):
            return jsonify({"error": "Invalid input"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Use parameterized queries to prevent SQL Injection
        cursor.execute('INSERT INTO products (product_name) VALUES (?)', (product_name,))
        product_id = cursor.lastrowid
        
        for tag in tags:
            cursor.execute('INSERT INTO tags (product_id, tag) VALUES (?, ?)', (product_id, tag))
        
        conn.commit()
        conn.close()
        return jsonify({"status": "Successful operation"}), 200
    except Exception:
        # Return documented error status code without leaking internal details
        return jsonify({"error": "Invalid input"}), 400

if __name__ == '__main__':
    init_db()
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)