import os
import sqlite3
import json
from flask import Flask, request, jsonify

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default-secret-key')

DB_NAME = 'db.sqlite3'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # We store the product name as a primary key and the unstructured properties as a JSON string
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
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body"}), 400
    
    name = data.get('name')
    if not name or not isinstance(name, str):
        return jsonify({"error": "Product name is required and must be a string"}), 400

    # Extract additional properties (everything except 'name')
    # The schema specifies additionalProperties are strings
    properties = {k: str(v) for k, v in data.items() if k != 'name'}
    
    try:
        with get_db_connection() as conn:
            conn.execute('INSERT INTO products (name, properties) VALUES (?, ?)', 
                         (name, json.dumps(properties)))
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Product with this name already exists"}), 400
    
    return jsonify({"message": "Product successfully added"}), 201

@app.route('/download', methods=['GET'])
def download_product():
    name = request.args.get('name')
    if not name:
        return jsonify({"error": "Product name is required"}), 400

    with get_db_connection() as conn:
        row = conn.execute('SELECT properties FROM products WHERE name = ?', (name,)).fetchone()
        
    if row is None:
        return jsonify({"error": "Product not found"}), 404

    # The schema asks for the data of a product as a string in the 'data' field
    # We return the JSON string of the properties
    return jsonify({"data": row['properties']}), 200

@app.route('/upload', methods=['POST'])
def upload_product():
    data = request.get_json()
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body"}), 400
    
    name = data.get('name')
    product_data = data.get('data')
    
    if not name or not product_data or not isinstance(product_data, str):
        return jsonify({"error": "Invalid upload query: name and data are required"}), 400

    # Validate that 'data' is actually a valid JSON string of properties
    try:
        json.loads(product_data)
    except json.JSONDecodeError:
        return jsonify({"error": "Data field must be a valid JSON string"}), 400

    with get_db_connection() as conn:
        cursor = conn.execute('UPDATE products SET properties = ? WHERE name = ?', (product_data, name))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "Product not found in catalog"}), 404

    return jsonify({"message": "The product with the given name was updated"}), 200

@app.route('/search', methods=['GET'])
def search_products():
    query = request.args.get('query')
    if not query:
        return jsonify({"error": "Search query is required"}), 400

    results = []
    with get_db_connection() as conn:
        # Fetch all products to perform search across unstructured properties
        rows = conn.execute('SELECT name, properties FROM products').fetchall()
        
    for row in rows:
        name = row['name']
        props = json.loads(row['properties'])
        
        # Check if query matches name or any property value
        match = (query.lower() in name.lower()) or \
                any(query.lower() in str(v).lower() for v in props.values())
        
        if match:
            product_entry = {"name": name}
            product_entry.update(props)
            results.append(product_entry)

    return jsonify({"results": results}), 200

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)