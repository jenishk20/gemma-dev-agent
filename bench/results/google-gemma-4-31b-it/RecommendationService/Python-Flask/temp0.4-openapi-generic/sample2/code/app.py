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
        # Create products table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL
            )
        ''')
        # Create tags table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    <title>Product Recommendations</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .product-item { border: 1px solid #ccc; padding: 10px; margin: 10px 0; border-radius: 5px; }
        .tag { background: #e0e0e0; padding: 2px 6px; margin-right: 5px; border-radius: 3px; font-size: 0.8em; }
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
    tags_query = request.args.get('tags')
    if not tags_query:
        return "Missing 'tags' query parameter", 400

    # Split tags by comma and strip whitespace
    search_tags = [t.strip() for t in tags_query.split(',') if t.strip()]
    
    if not search_tags:
        return render_template_string(HTML_TEMPLATE, products=[]), 200

    with get_db_connection() as conn:
        # Find products that have at least one of the provided tags
        # Using parameterized query to prevent SQL injection
        placeholders = ','.join(['?'] * len(search_tags))
        query = f'''
            SELECT p.id, p.product_name 
            FROM products p 
            JOIN tags t ON p.id = t.product_id 
            WHERE t.tag IN ({placeholders}) 
            GROUP BY p.id
        '''
        cursor = conn.execute(query, search_tags)
        matched_products = cursor.fetchall()

        results = []
        for row in matched_products:
            # Fetch all tags for this specific product
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
        return jsonify({"error": "Invalid JSON"}), 400

    product_name = data.get('product_name')
    tags = data.get('tags')

    if not product_name or not isinstance(tags, list):
        return jsonify({"error": "Invalid input: product_name (string) and tags (list) are required"}), 400

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Insert product
            cursor.execute('INSERT INTO products (product_name) VALUES (?)', (product_name,))
            product_id = cursor.lastrowid
            
            # Insert tags
            tag_data = [(product_id, tag) for tag in tags]
            cursor.executemany('INSERT INTO tags (product_id, tag) VALUES (?, ?)', tag_data)
            conn.commit()
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"message": "Successful operation"}), 200

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)