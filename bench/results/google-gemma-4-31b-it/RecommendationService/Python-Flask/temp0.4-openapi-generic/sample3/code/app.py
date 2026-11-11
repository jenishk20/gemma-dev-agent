import os
import sqlite3
from flask import Flask, request, render_template_string, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key_for_dev")

DB_FILE = "db.sqlite3"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
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
RECOMMENDATION_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
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
    <a href="/">Back to Home</a>
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
        return render_template_string(RECOMMENDATION_TEMPLATE, products=[]), 200

    with get_db_connection() as conn:
        # Find products that have at least one of the tags
        # Using parameterized query to prevent SQL injection
        placeholders = ','.join(['?'] * len(search_tags))
        query = f'''
            SELECT p.product_name, p.id 
            FROM products p 
            JOIN tags t ON p.id = t.product_id 
            WHERE t.tag IN ({placeholders}) 
            GROUP BY p.id
        '''
        cursor = conn.execute(query, search_tags)
        matched_products = cursor.fetchall()

        results = []
        for row in matched_products:
            # Fetch all tags for this specific product to display them
            tag_cursor = conn.execute('SELECT tag FROM tags WHERE product_id = ?', (row['id'],))
            product_tags = [t['tag'] for t in tag_cursor.fetchall()]
            results.append({
                'name': row['product_name'],
                'tags': product_tags
            })

    return render_template_string(RECOMMENDATION_TEMPLATE, products=results), 200

@app.route('/recommender', methods=['POST'])
def add_product():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input, JSON expected"}), 400

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
        return jsonify({"error": str(e)}), 400

    return jsonify({"message": "Successful operation"}), 200

@app.route('/')
def index():
    return "Welcome to the Product Recommendation Service. Use /recommender (GET/POST) as per API spec."

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)