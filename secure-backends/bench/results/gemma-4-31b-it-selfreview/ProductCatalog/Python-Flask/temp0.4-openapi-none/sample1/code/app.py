import os
import sqlite3
import json
from flask import Flask, request, jsonify

app = Flask(__name__)
# Use the provided APP_SECRET env variable
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default_secret_for_dev_only')

DB_PATH = 'db.sqlite3'

# Limit request body size to prevent resource exhaustion (e.g., 1MB)
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024

def get_db_connection():
    # Using a context manager for the connection ensures it is closed
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        with get_db_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    name TEXT PRIMARY KEY,
                    properties TEXT NOT NULL
                )
            ''')
            conn.commit()
    except Exception:
        # In a real production app, we would log this. 
        # Here we ensure the app doesn't crash during init.
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

        # Extract all other properties and ensure they are strings as per OpenAPI schema
        properties = {}
        for k, v in data.items():
            if k != 'name':
                if not isinstance(v, str):
                    return jsonify({"error": "Invalid input: properties must be strings"}), 400
                properties[k] = v
        
        with get_db_connection() as conn:
            # Parameterized query prevents SQL Injection
            conn.execute('INSERT INTO products (name, properties) VALUES (?, ?)', 
                         (name, json.dumps(properties)))
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Product already exists"}), 400
    except Exception:
        return jsonify({"error": "Internal server error"}), 400
    
    return '', 201

@app.route('/download', methods=['GET'])
def download_product():
    try:
        name = request.args.get('name')
        if not name:
            return jsonify({"error": "Invalid input"}), 400
        
        with get_db_connection() as conn:
            # Parameterized query prevents SQL Injection
            row = conn.execute('SELECT properties FROM products WHERE name = ?', (name,)).fetchone()
            
        if row is None:
            return jsonify({"error": "Product not found"}), 400 # Mapping to 400 as per "Invalid input" logic
        
        return jsonify({"data": row['properties']}), 200
    except Exception:
        return jsonify({"error": "Internal server error"}), 400

@app.route('/upload', methods=['POST'])
def upload_product():
    try:
        data = request.get_json(silent=True)
        if not data or not isinstance(data, dict) or 'name' not in data or 'data' not in data:
            return jsonify({"error": "Invalid upload query"}), 400
        
        name = data['name']
        properties_json = data['data']
        
        if not isinstance(name, str) or not isinstance(properties_json, str):
            return jsonify({"error": "Invalid upload query"}), 400
        
        # Validate that 'data' is a valid JSON string representing an object (safe deserialization)
        try:
            parsed_props = json.loads(properties_json)
            if not isinstance(parsed_props, dict):
                raise ValueError("Not a JSON object")
            # Ensure all values in the uploaded JSON are strings to maintain catalog consistency
            if not all(isinstance(v, str) for v in parsed_props.values()):
                return jsonify({"error": "Invalid upload query"}), 400
        except (json.JSONDecodeError, ValueError):
            return jsonify({"error": "Invalid upload query"}), 400

        with get_db_connection() as conn:
            # Parameterized query prevents SQL Injection
            conn.execute('INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)', 
                         (name, properties_json))
            conn.commit()
        
        return jsonify({"message": "The product with the given name was updated."}), 200
    except Exception:
        return jsonify({"error": "Internal server error"}), 400

@app.route('/search', methods=['GET'])
def search_products():
    try:
        query = request.args.get('query')
        if query is None:
            return jsonify({"error": "Invalid search query"}), 400
        
        results = []
        with get_db_connection() as conn:
            # We fetch records and filter. To prevent resource exhaustion on massive DBs, 
            # we use a generator/iterator.
            cursor = conn.execute('SELECT name, properties FROM products')
            for row in cursor:
                name = row['name']
                try:
                    props = json.loads(row['properties'])
                except json.JSONDecodeError:
                    continue
                
                # Case-insensitive search
                search_term = query.lower()
                if (search_term in name.lower()) or \
                   any(search_term in str(v).lower() for v in props.values()):
                    
                    product = {"name": name}
                    product.update(props)
                    results.append(product)
                
        return jsonify({"results": results}), 200
    except Exception:
        return jsonify({"error": "Internal server error"}), 400

if __name__ == '__main__':
    init_db()
    # Port 5000, 0.0.0.0 as requested
    app.run(host='0.0.0.0', port=5000)