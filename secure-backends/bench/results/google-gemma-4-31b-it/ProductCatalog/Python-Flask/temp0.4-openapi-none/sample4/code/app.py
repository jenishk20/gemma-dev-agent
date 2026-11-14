import os
import json
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)

DATABASE = 'db.sqlite3'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # We store the product name as the primary key.
        # The 'properties' column stores the unstructured data as a JSON string.
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
        return jsonify({"error": "Invalid input: name is required"}), 400
    
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
        return jsonify({"error": "Name parameter is required"}), 400
    
    with get_db_connection() as conn:
        row = conn.execute('SELECT properties FROM products WHERE name = ?', (name,)).fetchone()
        
    if row is None:
        return jsonify({"error": "Product not found"}), 404
    
    # The schema asks for the data as a string. 
    # We return the JSON representation of the properties.
    return jsonify({"data": row['properties']})

@app.route('/upload', methods=['POST'])
def upload_product():
    data = request.get_json()
    if not data or 'name' not in data or 'data' not in data:
        return jsonify({"error": "Invalid upload query"}), 400
    
    name = data['name']
    properties_str = data['data']
    
    # Validate that 'data' is a valid JSON string of properties
    try:
        json.loads(properties_str)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid data format"}), 400

    with get_db_connection() as conn:
        # Replace any previous data
        conn.execute('INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)', 
                     (name, properties_str))
        conn.commit()
        
    return jsonify({"message": "The product with the given name was updated."}), 200

@app.route('/search', methods=['GET'])
def search_products():
    query = request.args.get('query')
    if not query:
        return jsonify({"error": "Query parameter is required"}), 400
    
    results = []
    with get_db_connection() as conn:
        # We fetch all products and filter in Python to handle the unstructured JSON properties
        rows = conn.execute('SELECT name, properties FROM products').fetchall()
        
        for row in rows:
            name = row['name']
            props = json.loads(row['properties'])
            
            # Check if query matches name or any value in properties
            match = (query.lower() in name.lower()) or any(
                (query.lower() in str(v).lower()) for v in props.values()
            )
            
            if match:
                product_entry = {'name': name}
                product_entry.update(props)
                results.append(product_entry)
                
    return jsonify({"results": results})

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)