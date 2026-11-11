import os
import sqlite3
import json
from flask import Flask, request, jsonify

app = Flask(__name__)
DATABASE = 'db.sqlite3'

# Resource exhaustion: Limit the maximum size of the request body to prevent DoS
# 1MB is generally sufficient for a product catalog entry
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024

def get_db():
    # Using a context manager for connection to ensure it closes
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        with get_db() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    name TEXT PRIMARY KEY,
                    properties TEXT
                )
            ''')
            conn.commit()
    except Exception:
        # In a production environment, we would log this, but we must not leak details
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
            
        # Extract all properties except 'name'. 
        # Ensure all values are strings as per the OpenAPI schema 'additionalProperties: type: string'
        properties = {}
        for k, v in data.items():
            if k != 'name':
                if not isinstance(v, str):
                    return jsonify({"error": "Invalid input: all properties must be strings"}), 400
                properties[k] = v
        
        with get_db() as conn:
            # Parameterized query prevents SQL Injection
            conn.execute('INSERT INTO products (name, properties) VALUES (?, ?)', 
                        (name, json.dumps(properties)))
            conn.commit()
        return '', 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Invalid input"}), 400
    except Exception:
        return jsonify({"error": "Internal server error"}), 400

@app.route('/download', methods=['GET'])
def download_product():
    try:
        name = request.args.get('name')
        if not name:
            return jsonify({"error": "Invalid input"}), 400
        
        with get_db() as conn:
            # Parameterized query prevents SQL Injection
            row = conn.execute('SELECT properties FROM products WHERE name = ?', (name,)).fetchone()
            
        if row is None:
            return jsonify({"error": "Product not found"}), 404
        
        return jsonify({"data": row['properties']}), 200
    except Exception:
        return jsonify({"error": "Internal server error"}), 400

@app.route('/upload', methods=['POST'])
def upload_product():
    try:
        data = request.get_json(silent=True)
        if data is None or not isinstance(data, dict) or 'name' not in data or 'data' not in data:
            return jsonify({"error": "Invalid upload query"}), 400
        
        name = data['name']
        properties_json = data['data']
        
        if not isinstance(name, str) or not isinstance(properties_json, str):
            return jsonify({"error": "Invalid upload query"}), 400
        
        # Deserialization check: Validate that 'data' is a valid JSON string of an object
        # and that all its values are strings to maintain catalog integrity
        try:
            parsed_props = json.loads(properties_json)
            if not isinstance(parsed_props, dict):
                raise ValueError("Not a JSON object")
            for v in parsed_props.values():
                if not isinstance(v, str):
                    raise ValueError("Properties must be strings")
        except (json.JSONDecodeError, ValueError):
            return jsonify({"error": "Invalid upload query"}), 400

        with get_db() as conn:
            # Parameterized query prevents SQL Injection
            conn.execute('REPLACE INTO products (name, properties) VALUES (?, ?)', 
                        (name, properties_json))
            conn.commit()
            
        return jsonify({"message": "Product updated"}), 200
    except Exception:
        return jsonify({"error": "Internal server error"}), 400

@app.route('/search', methods=['GET'])
def search_products():
    try:
        query = request.args.get('query')
        if query is None:
            return jsonify({"error": "Invalid search query"}), 400
        
        results = []
        with get_db() as conn:
            # We fetch all records. To prevent resource exhaustion on massive DBs, 
            # we would normally use LIMIT/OFFSET or a search index.
            rows = conn.execute('SELECT name, properties FROM products').fetchall()
            
            query_lower = query.lower()
            for row in rows:
                name = row['name']
                try:
                    props = json.loads(row['properties'])
                except (json.JSONDecodeError, TypeError):
                    props = {}
                
                # Case-insensitive search in name or any property value
                match = (query_lower in name.lower()) or \
                        any(query_lower in str(v).lower() for v in props.values())
                
                if match:
                    product = {"name": name}
                    product.update(props)
                    results.append(product)
                    
        return jsonify({"results": results}), 200
    except Exception:
        return jsonify({"error": "Invalid search query"}), 400

if __name__ == '__main__':
    init_db()
    # Running on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)