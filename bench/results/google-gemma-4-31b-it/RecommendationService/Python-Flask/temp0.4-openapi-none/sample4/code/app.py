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
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>Product Recommendations</title></head>
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
    tags_query = request.args.get('tags')
    if not tags_query:
        return "Missing tags parameter", 400

    # Split tags by comma and strip whitespace
    search_tags = [t.strip() for t in tags_query.split(',') if t.strip()]
    
    if not search_tags:
        return render_template_string(HTML_TEMPLATE, products=[]), 200

    conn = get_db_connection()
    # Find products that have at least one of the provided tags
    # Using a parameterized query to prevent SQL injection
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

@app.route('/recommender', methods=['POST'])
def post_product():
    data = request.get_json()
    if not data or 'product_name' not in data or 'tags' not in data:
        return jsonify({"error": "Invalid input"}), 400
    
    product_name = data['product_name']
    tags = data['tags']

    if not isinstance(tags, list):
        return jsonify({"error": "Tags must be a list"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert product
        cursor.execute('INSERT INTO products (product_name) VALUES (?)', (product_name,))
        product_id = cursor.lastrowid
        
        # Insert tags
        for tag in tags:
            cursor.execute('INSERT INTO tags (product_id, tag) VALUES (?, ?)', (product_id, tag))
        
        conn.commit()
        conn.close()
        return jsonify({"status": "Successful operation"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)