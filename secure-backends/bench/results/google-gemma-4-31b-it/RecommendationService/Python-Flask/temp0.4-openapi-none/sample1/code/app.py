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
                product_id INTEGER,
                tag TEXT NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        ''')
        conn.commit()

# HTML Template for the recommendation results
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
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
    if not tags_query:
        return "Missing 'tags' query parameter", 400

    # Split tags by comma and clean whitespace
    search_tags = [t.strip() for t in tags_query.split(',') if t.strip()]
    
    if not search_tags:
        return render_template_string(HTML_TEMPLATE, tags_searched=tags_query, products=[]), 200

    conn = get_db_connection()
    # Find products that have at least one of the tags
    # We use a JOIN to get the product name and then a separate query or grouping to get all tags for those products
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
        # Get all tags for this specific product to display them
        product_tags = conn.execute('SELECT tag FROM tags WHERE product_id = ?', (row['id'],)).fetchall()
        results.append({
            'name': row['product_name'],
            'tags': [t['tag'] for t in product_tags]
        })
    
    conn.close()
    return render_template_string(HTML_TEMPLATE, tags_searched=tags_query, products=results), 200

@app.route('/recommender', methods=['POST'])
def post_product():
    data = request.get_json()
    if not data or 'product_name' not in data or 'tags' not in data:
        return jsonify({"error": "Invalid input"}), 400
    
    product_name = data['product_name']
    tags = data['tags']
    
    if not isinstance(tags, list):
        return jsonify({"error": "Tags must be an array"}), 400

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
        return jsonify({"message": "Successful operation"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Basic root route for convenience
@app.route('/')
def index():
    return 'Welcome to the Recommendation Service. Use GET /recommender?tags=tag1,tag2 or POST /recommender'

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)