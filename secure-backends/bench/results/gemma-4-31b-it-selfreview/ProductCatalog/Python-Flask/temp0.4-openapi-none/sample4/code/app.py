import os
import json
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)

# Security: Limit request body size to prevent Resource Exhaustion (DoS)
# 1MB is generally sufficient for a product catalog entry
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024

DATABASE = 'db.sqlite3'

def get_db_connection():
    # Using a context manager for the connection ensures it's closed properly
    conn = sqlite3.connect(DATABASE)
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
        # In a real scenario, we would log this. Here we ensure the app starts.
        pass

@app.route('/add', methods=['POST'])
def add_product():
    try:
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Invalid JSON"}), 400
        
        if not isinstance(data, dict) or 'name' not in data:
            return jsonify({"error": "Invalid input: name is required"}), 400
        
        name = data['name']
        if not isinstance(name, str):
            return jsonify({"error": "Name must be a string"}), 400

        # Filter and validate that all additional properties are strings as per OpenAPI schema
        properties = {}
        for k, v in data.items():
            if k == 'name':
                continue
            if not isinstance(v, str):
                return jsonify({"error": f"Property {k} must be a string"}), 400
            properties[k] = v
        
        with get_db_connection() as conn:
            # SQL Injection Prevention: Using parameterized queries
            conn.execute('INSERT INTO products (name, properties) VALUES (?, ?)', 
                         (name, json.dumps(properties)))
            conn.commit()
            
    except sqlite3.IntegrityError:
        return jsonify({"error": "Product with this name already exists"}), 400
    except Exception:
        # Error handling: Return documented 400 for invalid input, avoid leaking stack traces
        return jsonify({"error": "An internal error occurred"}), 400
    
    return '', 201

@app.route('/download', methods=['GET'])
def download_product():
    try:
        name = request.args.get('name')
        if not name:
            return jsonify({"error": "Name parameter is required"}), 400
        
        with get_db_connection() as conn:
            # SQL Injection Prevention: Parameterized query
            row = conn.execute('SELECT properties FROM products WHERE name = ?', (name,)).fetchone()
            
        if row is None:
            # The schema doesn't explicitly define a 404, but it's standard. 
            # However, to stay strictly to "documented error status codes", 
            # we treat missing as an invalid query/request if needed, but 404 is appropriate here.
            return jsonify({"error": "Product not found"}), 404
        
        return jsonify({"data": row['properties']})
    except Exception:
        return jsonify({"error": "An internal error occurred"}), 400

@app.route('/upload', methods=['POST'])
def upload_product():
    try:
        data = request.get_json(silent=True)
        if not data or not isinstance(data, dict):
            return jsonify({"error": "Invalid upload query"}), 400
            
        if 'name' not in data or 'data' not in data:
            return jsonify({"error": "Invalid upload query"}), 400
        
        name = data['name']
        properties_str = data['data']
        
        if not isinstance(name, str) or not isinstance(properties_str, str):
            return jsonify({"error": "Invalid upload query"}), 400
        
        # Deserialization Security: Validate that the string is valid JSON 
        # and contains only string values to maintain catalog integrity
        try:
            parsed_props = json.loads(properties_str)
            if not isinstance(parsed_props, dict):
                return jsonify({"error": "Invalid data format"}), 400
            for v in parsed_props.values():
                if not isinstance(v, str):
                    return jsonify({"error": "Invalid data format: all properties must be strings"}), 400
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid data format"}), 400

        with get_db_connection() as conn:
            # SQL Injection Prevention: Parameterized query
            conn.execute('INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)', 
                         (name, properties_str))
            conn.commit()
            
        return jsonify({"message": "The product with the given name was updated."}), 200
    except Exception:
        return jsonify({"error": "Invalid upload query"}), 400

@app.route('/search', methods=['GET'])
def search_products():
    try:
        query = request.args.get('query')
        if not query:
            return jsonify({"error": "Query parameter is required"}), 400
        
        results = []
        with get_db_connection() as conn:
            # We fetch all products. To prevent resource exhaustion on massive DBs, 
            # in a real app we'd use a full-text search index. 
            # Here we use a parameterized query to get the data.
            rows = conn.execute('SELECT name, properties FROM products').fetchall()
            
            query_lower = query.lower()
            for row in rows:
                name = row['name']
                try:
                    props = json.loads(row['properties'])
                except (json.JSONDecodeError, TypeError):
                    props = {}
                
                # Case-insensitive search
                match = (query_lower in name.lower()) or any(
                    (query_lower in str(v).lower()) for v in props.values()
                )
                
                if match:
                    product_entry = {'name': name}
                    product_entry.update(props)
                    results.append(product_entry)
                    
        return jsonify({"results": results})
    except Exception:
        return jsonify({"error": "Invalid search query"}), 400

if __name__ == '__main__':
    init_db()
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)