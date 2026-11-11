import os
import sqlite3
import json
from flask import Flask, request, jsonify

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default-secret-key')

DB_PATH = 'db.sqlite3'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # We store the product name as the primary key.
        # The 'properties' column stores a JSON string of all other attributes.
        conn.execute('''
            CREATE TABLE IF NOT EXISTS products (
                name TEXT PRIMARY KEY,
                properties TEXT
            )
        ''')
        conn.commit()

@app.route('/add', methods=['POST'])
def add_product():
    data = request.get_json()
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body"}), 400
    
    name = data.get('name')
    if not name or not isinstance(name, str):
        return jsonify({"error": "Missing or invalid required field: name"}), 400

    # Extract all other properties
    properties = {k: v for k, v in data.items() if k != 'name'}
    
    # Validate that all additional properties are strings as per OpenAPI schema
    for v in properties.values():
        if not isinstance(v, str):
            return jsonify({"error": "All additional properties must be strings"}), 400

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
        return jsonify({"error": "Missing required query parameter: name"}), 400

    with get_db_connection() as conn:
        row = conn.execute('SELECT * FROM products WHERE name = ?', (name,)).fetchone()
    
    if row is None:
        return jsonify({"error": "Product not found"}), 404

    # The schema asks for the data as a string. 
    # We reconstruct the full object (name + properties) and stringify it.
    props = json.loads(row['properties'])
    full_data = {"name": row['name']}
    full_data.update(props)
    
    return jsonify({"data": json.dumps(full_data)})

@app.route('/upload', methods=['POST'])
def upload_product():
    data = request.get_json()
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body"}), 400
    
    name = data.get('name')
    payload_data = data.get('data')
    
    if not name or not isinstance(name, str) or not payload_data or not isinstance(payload_data, str):
        return jsonify({"error": "Invalid upload query"}), 400

    try:
        # Parse the data string to ensure it's valid JSON and extract properties
        product_dict = json.loads(payload_data)
        if not isinstance(product_dict, dict) or 'name' not in product_dict:
            return jsonify({"error": "Invalid data format"}), 400
        
        # The schema says this replaces previous data for the product.
        # We use the 'name' from the root of the request body to identify the product.
        properties = {k: v for k, v in product_dict.items() if k != 'name'}
        
        # Validate properties are strings
        for v in properties.values():
            if not isinstance(v, str):
                return jsonify({"error": "All properties must be strings"}), 400

        with get_db_connection() as conn:
            conn.execute('REPLACE INTO products (name, properties) VALUES (?, ?)', 
                         (name, json.dumps(properties)))
            conn.commit()
    except (json.JSONDecodeError, sqlite3.Error):
        return jsonify({"error": "Invalid upload query"}), 400

    return jsonify({"message": "Product updated"}), 200

@app.route('/search', methods=['GET'])
def search_products():
    query = request.args.get('query')
    if not query:
        return jsonify({"error": "Missing required query parameter: query"}), 400

    results = []
    with get_db_connection() as conn:
        rows = conn.execute('SELECT * FROM products').fetchall()
        
    for row in rows:
        name = row['name']
        props = json.loads(row['properties'])
        
        # Check if query matches name or any value in properties
        match = (query.lower() in name.lower())
        if not match:
            for val in props.values():
                if query.lower() in val.lower():
                    match = True
                    break
        
        if match:
            product_obj = {"name": name}
            product_obj.update(props)
            results.append(product_obj)

    return jsonify({"results": results})

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)