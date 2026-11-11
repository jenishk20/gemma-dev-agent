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
<head>
    <title>Recommended Products</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        ul { list-style-type: none; padding: 0; }
        li { margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
        .tag { background: #eee; padding: 2px 5px; margin-right: 5px; font-size: 0.8em; border-radius: 3px; }
    </style>
</head>
<body>
    <h1>Recommended Products</h1>
    <ul>
        {% for product in products %}
        <li>
            <strong>{{ product.name }}</strong><br>
            Tags: {% for tag in product.tags %}<span class="tag">{{ tag }}</span>{% endfor %}
        </li>
        {% endfor %}
    </ul>
    {% if not products %}
    <p>No products found matching the provided tags.</p>
    {% endif %}
</body>
</html>
"""

@app.route('/recommender', methods=['GET'])
def get_recommendations():
    tags_query = request.args.get('tags')
    if not tags_query:
        return "Missing tags parameter", 400
    
    search_tags = [t.strip() for t in tags_query.split(',') if t.strip()]
    if not search_tags:
        return render_template_string(HTML_TEMPLATE, products=[]), 200

    conn = get_db_connection()
    # Find products that match at least one of the provided tags
    placeholders = ','.join(['?'] * len(search_tags))
    query = f'''
        SELECT DISTINCT p.id, p.product_name 
        FROM products p 
        JOIN tags t ON p.id = t.product_id 
        WHERE t.tag IN ({placeholders})
    '''
    products_rows = conn.execute(query, search_tags).fetchall()
    
    results = []
    for row in products_rows:
        # Get all tags for this specific product to display them
        p_tags = conn.execute('SELECT tag FROM tags WHERE product_id = ?', (row['id'],)).fetchall()
        results.append({
            'name': row['product_name'],
            'tags': [t['tag'] for t in p_tags]
        })
    
    conn.close()
    return render_template_string(HTML_TEMPLATE, products=results), 200

@app.route('/recommender', methods=['POST'])
def add_product():
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
        cursor.execute('INSERT INTO products (product_name) VALUES (?)', (product_name,))
        product_id = cursor.lastrowid
        
        for tag in tags:
            cursor.execute('INSERT INTO tags (product_id, tag) VALUES (?, ?)', (product_id, tag))
        
        conn.commit()
        conn.close()
        return jsonify({"message": "Successful operation"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)