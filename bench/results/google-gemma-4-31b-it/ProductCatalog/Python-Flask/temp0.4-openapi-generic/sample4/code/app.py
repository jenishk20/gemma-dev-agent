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
        # We store the product name as the primary key and the unstructured 
        # properties as a JSON string in a 'data' column.
        conn.execute('''
            CREATE TABLE IF NOT EXISTS products (
                name TEXT PRIMARY KEY,
                properties TEXT
            )
        ''')
        conn.commit()

@app.route('/add', methods=['POST'])
def add_product():
    body = request.get_json()
    if not body or not isinstance(body, dict):
        return jsonify({"error": "Invalid JSON"}), 400
    
    name = body.get('name')
    if not name or not isinstance(name, str):
        return jsonify({"error": "Missing or invalid product name"}), 400

    # Extract all other properties
    properties = {k: v for k, v in body.items() if k != 'name'}
    
    # Validate that all additional properties are strings as per OpenAPI schema
    for v in properties.values():
        if not isinstance(v, str):
            return jsonify({"error": "All additional properties must be strings"}), 400

    try:
        with get_db_connection() as conn:
            conn.execute('INSERT INTO products (name, properties) VALUES (?, ?)', 
                         (name, json.dumps(properties)))
            conn.commit()
        return '', 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Product already exists"}), 400

@app.route('/download', methods=['GET'])
def download_product():
    name = request.args.get('name')
    if not name:
        return jsonify({"error": "Missing name parameter"}), 400

    with get_db_connection() as conn:
        row = conn.execute('SELECT properties FROM products WHERE name = ?', (name,)).fetchone()
        
    if row is None:
        return jsonify({"error": "Product not found"}), 404

    # The schema asks for a response object with a 'data' property containing the product data
    # We return the properties JSON as a string inside the 'data' field
    return jsonify({"data": row['properties']}), 200

@app.route('/upload', methods=['POST'])
def upload_product():
    body = request.get_json()
    if not body or not isinstance(body, dict):
        return jsonify({"error": "Invalid JSON"}), 400
    
    name = body.get('name')
    data_str = body.get('data')
    
    if not name or not isinstance(name, str) or not data_str or not isinstance(data_str, str):
        return jsonify({"error": "Invalid upload query"}), 400

    try:
        # Validate that the data string is actually valid JSON and contains only strings
        props = json.loads(data_str)
        if not isinstance(props, dict):
            raise ValueError("Data must be a JSON object")
        for v in props.values():
            if not isinstance(v, str):
                raise ValueError("All properties must be strings")
                
        with get_db_connection() as conn:
            conn.execute('UPDATE products SET properties = ? WHERE name = ?', (data_str, name))
            if conn.total_changes == 0:
                # If product didn't exist, we can't update it, but the prompt says 
                # "upload data for a product with the given name", implying it exists.
                # However, to be robust, we check if it was updated.
                row = conn.execute('SELECT 1 FROM products WHERE name = ?', (name,)).fetchone()
                if not row:
                    return jsonify({"error": "Product not found"}), 400
            conn.commit()
        return jsonify({"message": "Product updated"}), 200
    except (json.JSONDecodeError, ValueError):
        return jsonify({"error": "Invalid data format"}), 400

@app.route('/search', methods=['GET'])
def search_products():
    query = request.args.get('query')
    if not query:
        return jsonify({"error": "Missing query parameter"}), 400

    results = []
    with get_db_connection() as conn:
        # Fetch all products and filter in Python to handle the unstructured JSON properties
        rows = conn.execute('SELECT name, properties FROM products').fetchall()
        
        for row in rows:
            name = row['name']
            props = json.loads(row['properties'])
            
            # Check if query is in name or any of the property values
            match = (query in name) or any(query in str(v) for v in props.values())
            
            if match:
                product_obj = {"name": name}
                product_obj.update(props)
                results.append(product_obj)

    return jsonify({"results": results}), 200

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)