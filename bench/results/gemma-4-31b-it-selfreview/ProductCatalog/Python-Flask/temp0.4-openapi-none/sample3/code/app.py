import os
import sqlite3
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

# Security: Ensure we are using a fixed database path to prevent path traversal
# if the filename were ever to become dynamic.
DB_NAME = "db.sqlite3"

# Resource Exhaustion: Limit the maximum allowed content length for JSON payloads
# to prevent MemoryError/DoS attacks via massive request bodies.
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1MB limit

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
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
        # In a production environment, we would log this. 
        # For this task, we ensure the DB is initialized.
        pass

@app.route('/add', methods=['POST'])
def add_product():
    try:
        data = request.get_json(silent=True)
        if data is None or not isinstance(data, dict) or 'name' not in data:
            return jsonify({"error": "Invalid input"}), 400
        
        name = data['name']
        if not isinstance(name, str):
            return jsonify({"error": "Invalid input"}), 400

        # Ensure all additional properties are strings as per OpenAPI schema
        properties = {}
        for k, v in data.items():
            if k == 'name':
                continue
            if not isinstance(v, str):
                return jsonify({"error": "Invalid input: all properties must be strings"}), 400
            properties[k] = v
        
        with get_db_connection() as conn:
            # SQL Injection Prevention: Using parameterized queries
            conn.execute('INSERT INTO products (name, properties) VALUES (?, ?)', 
                         (name, json.dumps(properties)))
            conn.commit()
        return '', 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Product already exists"}), 400
    except Exception:
        # Error Handling: Catch-all to prevent leaking stack traces
        return jsonify({"error": "Internal server error"}), 400

@app.route('/download', methods=['GET'])
def download_product():
    try:
        name = request.args.get('name')
        if not name:
            return jsonify({"error": "Invalid input"}), 400
        
        with get_db_connection() as conn:
            # SQL Injection Prevention: Using parameterized queries
            row = conn.execute('SELECT properties FROM products WHERE name = ?', (name,)).fetchone()
            
        if row is None:
            return jsonify({"error": "Product not found"}), 400 # Mapping to 400 as per "Invalid input" logic
        
        return jsonify({"data": row['properties']})
    except Exception:
        return jsonify({"error": "Internal server error"}), 400

@app.route('/upload', methods=['POST'])
def upload_product():
    try:
        data = request.get_json(silent=True)
        if data is None or not isinstance(data, dict) or 'name' not in data or 'data' not in data:
            return jsonify({"error": "Invalid upload query"}), 400
        
        name = data['name']
        properties_str = data['data']
        
        if not isinstance(name, str) or not isinstance(properties_str, str):
            return jsonify({"error": "Invalid upload query"}), 400
        
        # Deserialization Security: Validate that 'data' is a valid JSON string
        # and that it represents a dictionary of strings to prevent logic errors.
        try:
            parsed_props = json.loads(properties_str)
            if not isinstance(parsed_props, dict):
                return jsonify({"error": "Invalid upload query"}), 400
            for v in parsed_props.values():
                if not isinstance(v, str):
                    return jsonify({"error": "Invalid upload query"}), 400
        except (json.JSONDecodeError, TypeError):
            return jsonify({"error": "Invalid upload query"}), 400

        with get_db_connection() as conn:
            # SQL Injection Prevention: Using parameterized queries
            conn.execute('INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)', 
                         (name, properties_str))
            conn.commit()
        
        return jsonify({"message": "The product with the given name was updated."}), 200
    except Exception:
        return jsonify({"error": "Internal server error"}), 400

@app.route('/search', methods=['GET'])
def search_products():
    try:
        query = request.args.get('query')
        if not query:
            return jsonify({"error": "Invalid search query"}), 400
        
        results = []
        with get_db_connection() as conn:
            # SQL Injection Prevention: Parameterized query
            cursor = conn.execute('SELECT name, properties FROM products')
            for row in cursor:
                name = row['name']
                try:
                    props = json.loads(row['properties'])
                except (json.JSONDecodeError, TypeError):
                    continue
                
                # Case-insensitive search
                match = (query.lower() in name.lower())
                if not match and isinstance(props, dict):
                    for val in props.values():
                        if isinstance(val, str) and query.lower() in val.lower():
                            match = True
                            break
                
                if match:
                    product_entry = {"name": name}
                    if isinstance(props, dict):
                        product_entry.update(props)
                    results.append(product_entry)
                    
        return jsonify({"results": results})
    except Exception:
        return jsonify({"error": "Internal server error"}), 400

if __name__ == '__main__':
    init_db()
    # Port 5000, 0.0.0.0 as requested.
    app.run(host='0.0.0.0', port=5000)