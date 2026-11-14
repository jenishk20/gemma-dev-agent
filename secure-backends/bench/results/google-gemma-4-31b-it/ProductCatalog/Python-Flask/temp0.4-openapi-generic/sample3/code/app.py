import os
import sqlite3
import json
from flask import Flask, request, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key")

DB_PATH = "db.sqlite3"

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
                properties TEXT NOT NULL
            )
        ''')
        conn.commit()

@app.route('/add', methods=['POST'])
def add_product():
    data = request.get_json()
    if not data or not isinstance(data, dict) or 'name' not in data:
        return jsonify({"error": "Invalid input: 'name' is required"}), 400
    
    name = data['name']
    if not isinstance(name, str):
        return jsonify({"error": "Name must be a string"}), 400

    # Validate that all additional properties are strings as per OpenAPI schema
    for key, value in data.items():
        if not isinstance(value, str):
            return jsonify({"error": f"Property {key} must be a string"}), 400

    try:
        with get_db_connection() as conn:
            # Store the whole object as a JSON string
            conn.execute('INSERT INTO products (name, properties) VALUES (?, ?)', 
                         (name, json.dumps(data)))
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Product with this name already exists"}), 400
    
    return jsonify({"message": "Product successfully added"}), 201

@app.route('/download', methods=['GET'])
def download_product():
    name = request.args.get('name')
    if not name:
        return jsonify({"error": "Query parameter 'name' is required"}), 400

    with get_db_connection() as conn:
        row = conn.execute('SELECT properties FROM products WHERE name = ?', (name,)).fetchone()
    
    if row:
        # The schema asks for the data as a string inside a 'data' property
        return jsonify({"data": row['properties']}), 200
    else:
        return jsonify({"error": "Product not found"}), 404

@app.route('/upload', methods=['POST'])
def upload_product():
    data = request.get_json()
    if not data or not isinstance(data, dict) or 'name' not in data or 'data' not in data:
        return jsonify({"error": "Invalid upload query: 'name' and 'data' are required"}), 400

    name = data['name']
    raw_data = data['data']

    try:
        # Validate that the provided data string is a valid JSON object and contains the name
        product_json = json.loads(raw_data)
        if not isinstance(product_json, dict) or product_json.get('name') != name:
            return jsonify({"error": "Data content does not match product name"}), 400
        
        # Ensure all properties in the uploaded data are strings
        for val in product_json.values():
            if not isinstance(val, str):
                return jsonify({"error": "All product properties must be strings"}), 400

        with get_db_connection() as conn:
            conn.execute('INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)', 
                         (name, raw_data))
            conn.commit()
    except (json.JSONDecodeError, TypeError):
        return jsonify({"error": "Invalid JSON format in data field"}), 400

    return jsonify({"message": "The product with the given name was updated"}), 200

@app.route('/search', methods=['GET'])
def search_products():
    query = request.args.get('query')
    if not query:
        return jsonify({"error": "Query parameter 'query' is required"}), 400

    results = []
    with get_db_connection() as conn:
        # Fetch all products and filter in Python to handle unstructured JSON properties
        rows = conn.execute('SELECT properties FROM products').fetchall()
        
    for row in rows:
        product = json.loads(row['properties'])
        # Search if query is present in any of the string values
        if any(query.lower() in str(val).lower() for val in product.values()):
            results.append(product)

    return jsonify({"results": results}), 200

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)