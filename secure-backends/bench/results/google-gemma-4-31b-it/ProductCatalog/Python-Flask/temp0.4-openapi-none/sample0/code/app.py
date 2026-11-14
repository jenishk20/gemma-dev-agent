import os
import sqlite3
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

DB_PATH = 'db.sqlite3'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # We store the product name as the primary key.
        # The 'properties' column stores a JSON string of all attributes including the name.
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
    if not data or 'name' not in data:
        return jsonify({"error": "Invalid input: 'name' is required"}), 400
    
    name = data['name']
    # Store the entire object as a JSON string to handle unstructured properties
    properties_json = json.dumps(data)
    
    try:
        with get_db_connection() as conn:
            conn.execute('INSERT INTO products (name, properties) VALUES (?, ?)', (name, properties_json))
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
        
    if row:
        # The schema asks for a response object with a 'data' field containing the product data as a string
        return jsonify({"data": row['properties']}), 200
    else:
        return jsonify({"error": "Product not found"}), 400

@app.route('/upload', methods=['POST'])
def upload_product():
    data = request.get_json()
    if not data or 'name' not in data or 'data' not in data:
        return jsonify({"error": "Invalid upload query"}), 400
    
    name = data['name']
    properties_str = data['data']
    
    # Validate that the provided data string is valid JSON
    try:
        json.loads(properties_str)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid data format"}), 400

    with get_db_connection() as conn:
        # Fully replaces any previous data for the product
        conn.execute('INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)', (name, properties_str))
        conn.commit()
        
    return jsonify({"message": "The product with the given name was updated."}), 200

@app.route('/search', methods=['GET'])
def search_products():
    query = request.args.get('query')
    if not query:
        return jsonify({"error": "Query parameter 'query' is required"}), 400
    
    results = []
    with get_db_connection() as conn:
        rows = conn.execute('SELECT properties FROM products').fetchall()
        
    for row in rows:
        product_dict = json.loads(row['properties'])
        # Search matches if query is found in any of the string values of the product properties
        match = False
        for value in product_dict.values():
            if isinstance(value, str) and query.lower() in value.lower():
                match = True
                break
        
        if match:
            results.append(product_dict)
            
    return jsonify({"results": results}), 200

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)