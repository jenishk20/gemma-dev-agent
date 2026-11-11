import os
import sqlite3
import json
from flask import Flask, request, jsonify

app = Flask(__name__)
DATABASE = 'db.sqlite3'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        # We store the product name as the primary key and the unstructured 
        # properties as a JSON string to handle the 'additionalProperties' requirement.
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
    # Extract all properties except 'name' to store as unstructured data
    properties = {k: v for k, v in data.items() if k != 'name'}
    
    try:
        with get_db() as conn:
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
    
    with get_db() as conn:
        row = conn.execute('SELECT properties FROM products WHERE name = ?', (name,)).fetchone()
        
    if row is None:
        return jsonify({"error": "Product not found"}), 404
    
    # The schema asks for the data as a string. We return the JSON string of properties.
    return jsonify({"data": row['properties']}), 200

@app.route('/upload', methods=['POST'])
def upload_product():
    data = request.get_json()
    if not data or 'name' not in data or 'data' not in data:
        return jsonify({"error": "Invalid upload query"}), 400
    
    name = data['name']
    properties_json = data['data']
    
    # Validate that 'data' is a valid JSON string of an object
    try:
        json.loads(properties_json)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid data format"}), 400

    with get_db() as conn:
        conn.execute('REPLACE INTO products (name, properties) VALUES (?, ?)', 
                    (name, properties_json))
        conn.commit()
        
    return jsonify({"message": "Product updated"}), 200

@app.route('/search', methods=['GET'])
def search_products():
    query = request.args.get('query')
    if query is None:
        return jsonify({"error": "Query parameter 'query' is required"}), 400
    
    results = []
    with get_db() as conn:
        rows = conn.execute('SELECT name, properties FROM products').fetchall()
        
        for row in rows:
            name = row['name']
            props = json.loads(row['properties'])
            
            # Check if query matches name or any value in the unstructured properties
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