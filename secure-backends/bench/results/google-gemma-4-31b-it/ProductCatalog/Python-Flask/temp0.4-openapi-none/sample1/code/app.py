import os
import sqlite3
import json
from flask import Flask, request, jsonify

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default_secret')

DB_PATH = 'db.sqlite3'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # We store the product name as the primary key.
        # The unstructured properties are stored as a JSON string in the 'properties' column.
        conn.execute('''
            CREATE TABLE IF NOT EXISTS products (
                name TEXT PRIMARY KEY,
                properties TEXT NOT NULL
            )
        ''')
        conn.commit()

@app.route('/add', methods=['POST'])
def add_product():
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({"error": "Invalid input: 'name' is required"}), 400
    
    name = data['name']
    # Extract all other properties
    properties = {k: v for k, v in data.items() if k != 'name'}
    
    try:
        with get_db_connection() as conn:
            conn.execute('INSERT INTO products (name, properties) VALUES (?, ?)', 
                         (name, json.dumps(properties)))
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Product with this name already exists"}), 400
    
    return '', 201

@app.route('/download', methods=['GET'])
def download_product():
    name = request.args.get('name')
    if not name:
        return jsonify({"error": "Query parameter 'name' is required"}), 400
    
    with get_db_connection() as conn:
        row = conn.execute('SELECT properties FROM products WHERE name = ?', (name,)).fetchone()
        
    if row is None:
        return jsonify({"error": "Product not found"}), 404
    
    # The schema asks for the data as a string. 
    # Since we store properties as JSON, we return that JSON string.
    return jsonify({"data": row['properties']}), 200

@app.route('/upload', methods=['POST'])
def upload_product():
    data = request.get_json()
    if not data or 'name' not in data or 'data' not in data:
        return jsonify({"error": "Invalid upload query"}), 400
    
    name = data['name']
    properties_json = data['data']
    
    # Validate that 'data' is a valid JSON string representing an object
    try:
        json.loads(properties_json)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid data format"}), 400

    with get_db_connection() as conn:
        # Fully replace previous data
        conn.execute('INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)', 
                     (name, properties_json))
        conn.commit()
    
    return jsonify({"message": "Product updated"}), 200

@app.route('/search', methods=['GET'])
def search_products():
    query = request.args.get('query')
    if not query:
        return jsonify({"error": "Query parameter 'query' is required"}), 400
    
    results = []
    with get_db_connection() as conn:
        # Fetch all products and filter in Python to handle the unstructured JSON properties
        cursor = conn.execute('SELECT name, properties FROM products')
        for row in cursor:
            name = row['name']
            props = json.loads(row['properties'])
            
            # Match if query is in name or any of the property values
            match = (query.lower() in name.lower()) or \
                    any(query.lower() in str(v).lower() for v in props.values())
            
            if match:
                product = {"name": name}
                product.update(props)
                results.append(product)
                
    return jsonify({"results": results}), 200

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)