import os
import sqlite3
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

# Security: Ensure the database path is fixed and not derived from user input
DB_PATH = 'db.sqlite3'

# Resource Exhaustion: Limit the maximum content length for JSON payloads
# 1MB is generally sufficient for a product catalog entry and prevents memory exhaustion
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024

def get_db_connection():
    # Using a context manager for the connection ensures it is closed properly
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        with get_db_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    name TEXT PRIMARY KEY,
                    properties TEXT
                )
            ''')
            conn.commit()
    except Exception:
        # Internal initialization error; in a real app, we would log this
        pass

@app.route('/add', methods=['POST'])
def add_product():
    # Error handling: catch JSON parsing errors (400 Bad Request)
    try:
        data = request.get_json(silent=True)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    if data is None or not isinstance(data, dict) or 'name' not in data:
        return jsonify({"error": "Invalid input: 'name' is required"}), 400
    
    name = data['name']
    if not isinstance(name, str):
        return jsonify({"error": "Product name must be a string"}), 400

    # Deserialization/Input Validation: Ensure all additional properties are strings as per OpenAPI
    # This prevents injection of complex types that might crash the search logic
    for key, value in data.items():
        if not isinstance(value, str):
            return jsonify({"error": f"Property {key} must be a string"}), 400

    properties_json = json.dumps(data)
    
    try:
        with get_db_connection() as conn:
            # SQL Injection Prevention: Using parameterized queries (?)
            conn.execute('INSERT INTO products (name, properties) VALUES (?, ?)', (name, properties_json))
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Product with this name already exists"}), 400
    except Exception:
        return jsonify({"error": "Internal server error"}), 400
    
    return '', 201

@app.route('/download', methods=['GET'])
def download_product():
    name = request.args.get('name')
    if not name:
        return jsonify({"error": "Query parameter 'name' is required"}), 400
    
    try:
        with get_db_connection() as conn:
            # SQL Injection Prevention: Parameterized query
            row = conn.execute('SELECT properties FROM products WHERE name = ?', (name,)).fetchone()
            
        if row:
            return jsonify({"data": row['properties']}), 200
        else:
            return jsonify({"error": "Product not found"}), 400
    except Exception:
        return jsonify({"error": "Internal server error"}), 400

@app.route('/upload', methods=['POST'])
def upload_product():
    try:
        data = request.get_json(silent=True)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    if data is None or not isinstance(data, dict) or 'name' not in data or 'data' not in data:
        return jsonify({"error": "Invalid upload query"}), 400
    
    name = data['name']
    properties_str = data['data']
    
    if not isinstance(name, str) or not isinstance(properties_str, str):
        return jsonify({"error": "Invalid input types"}), 400
    
    # Deserialization Security: Validate that the data string is valid JSON and contains only strings
    try:
        parsed_data = json.loads(properties_str)
        if not isinstance(parsed_data, dict):
            return jsonify({"error": "Data must be a JSON object"}), 400
        for key, value in parsed_data.items():
            if not isinstance(value, str):
                return jsonify({"error": f"Property {key} must be a string"}), 400
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid data format"}), 400

    try:
        with get_db_connection() as conn:
            # SQL Injection Prevention: Parameterized query
            conn.execute('INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)', (name, properties_str))
            conn.commit()
    except Exception:
        return jsonify({"error": "Internal server error"}), 400
        
    return jsonify({"message": "The product with the given name was updated."}), 200

@app.route('/search', methods=['GET'])
def search_products():
    query = request.args.get('query')
    if not query:
        return jsonify({"error": "Query parameter 'query' is required"}), 400
    
    results = []
    try:
        with get_db_connection() as conn:
            # Resource Exhaustion: In a massive DB, this would be slow. 
            # However, the spec requires searching "any other property" (unstructured).
            # We fetch and filter in Python to avoid complex/dangerous dynamic SQL generation.
            rows = conn.execute('SELECT properties FROM products').fetchall()
            
        for row in rows:
            try:
                product_dict = json.loads(row['properties'])
                # Case-insensitive search as per common catalog behavior
                match = False
                for value in product_dict.values():
                    if isinstance(value, str) and query.lower() in value.lower():
                        match = True
                        break
                
                if match:
                    results.append(product_dict)
            except (json.JSONDecodeError, TypeError):
                continue # Skip corrupted entries
                
        return jsonify({"results": results}), 200
    except Exception:
        return jsonify({"error": "Internal server error"}), 400

if __name__ == '__main__':
    init_db()
    # Port 5000, 0.0.0.0 as requested
    app.run(host='0.0.0.0', port=5000)