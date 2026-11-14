import os
import sqlite3
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key_for_dev")

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
<head>
    <title>Recommended Products</title>
    <style>
        body { font-family: sans-serif; margin: 20px; }
        ul { list-style-type: none; padding: 0; }
        li { margin-bottom: 10px; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
        .product-name { font-weight: bold; font-size: 1.2em; }
        .tag-pill { background: #eee; padding: 2px 8px; border-radius: 10px; font-size: 0.8em; margin-right: 5px; }
    </style>
</head>
<body>
    <h1>Recommended Products</h1>
    {% if products %}
        <ul>
        {% for product in products %}
            <li>
                <span class="product-name">{{ product.name }}</span><br>
                {% for tag in product.tags %}
                    <span class="tag-pill">{{ tag }}</span>
                {% endfor %}
            </li>
        {% endfor %}
        </ul>
    {% else %}
        <p>No products found matching the provided tags.</p>
    {% endif %}
    <hr>
    <p><a href="/">Back to search</a></p>
</body>
</html>
"""

@app.route('/recommender', methods=['GET'])
def get_recommendations():
    tags_query = request.args.get('tags')
    if not tags_query:
        return "Missing 'tags' query parameter", 400

    # Split comma separated tags and clean whitespace
    search_tags = [t.strip() for t in tags_query.split(',') if t.strip()]
    
    if not search_tags:
        return render_template_string(HTML_TEMPLATE, products=[]), 200

    with get_db_connection() as conn:
        # Find products that have at least one of the provided tags
        # Using parameterized query to prevent SQL injection
        placeholders = ','.join(['?'] * len(search_tags))
        query = f'''
            SELECT DISTINCT p.id, p.product_name 
            FROM products p 
            JOIN tags t ON p.id = t.product_id 
            WHERE t.tag IN ({placeholders})
        '''
        cursor = conn.execute(query, search_tags)
        matching_products = cursor.fetchall()

        results = []
        for row in matching_products:
            # Get all tags for this specific product to display them
            tag_cursor = conn.execute('SELECT tag FROM tags WHERE product_id = ?', (row['id'],))
            product_tags = [t['tag'] for t in tag_cursor.fetchall()]
            results.append({
                'name': row['product_name'],
                'tags': product_tags
            })

    return render_template_string(HTML_TEMPLATE, products=results), 200

@app.route('/recommender', methods=['POST'])
def post_product():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input, JSON required"}), 400

    product_name = data.get('product_name')
    tags = data.get('tags')

    if not product_name or not isinstance(tags, list):
        return jsonify({"error": "Invalid input: product_name (string) and tags (list) are required"}), 400

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO products (product_name) VALUES (?)', (product_name,))
            product_id = cursor.lastrowid
            
            for tag in tags:
                if isinstance(tag, str):
                    cursor.execute('INSERT INTO tags (product_id, tag) VALUES (?, ?)', (product_id, tag.strip()))
            
            conn.commit()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"message": "Successful operation"}), 200

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)