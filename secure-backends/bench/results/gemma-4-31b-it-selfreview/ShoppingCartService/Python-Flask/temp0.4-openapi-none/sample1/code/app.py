import os
import sqlite3
import uuid
from flask import Flask, request, jsonify

app = Flask(__name__)
# Use the provided APP_SECRET env variable for the secret key
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key")

# Hardcoded database path to prevent path traversal
DB_PATH = "db.sqlite3"

def get_db_connection():
    # Using a fixed path prevents untrusted input from reaching file paths
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        with get_db_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS carts (
                    cart_id TEXT PRIMARY KEY
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS cart_items (
                    cart_id TEXT,
                    item_id INTEGER,
                    count INTEGER,
                    PRIMARY KEY (cart_id, item_id),
                    FOREIGN KEY (cart_id) REFERENCES carts (cart_id)
                )
            ''')
            conn.commit()
    except Exception:
        # Internal initialization error
        pass

@app.route('/create_cart', methods=['POST'])
def create_cart():
    try:
        # Use cryptographically secure randomness for IDs
        cart_id = str(uuid.uuid4())
        with get_db_connection() as conn:
            # Parameterized query to prevent SQL injection
            conn.execute('INSERT INTO carts (cart_id) VALUES (?)', (cart_id,))
            conn.commit()
        return jsonify({"cart_id": cart_id}), 201
    except Exception:
        return jsonify({"error": "Internal server error"}), 500

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    try:
        # Resource exhaustion: limit request body size (Flask default is usually 16MB, 
        # but we ensure we only process JSON)
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Invalid request"}), 400
            
        # Validate input types and presence to prevent unexpected behavior or crashes
        if not all(k in data for k in ('cart_id', 'item_id', 'count')):
            return jsonify({"error": "Invalid request"}), 400
        
        cart_id = data['cart_id']
        item_id = data['item_id']
        count = data['count']

        # Strict type checking to prevent logic errors or SQL injection via non-string/int types
        if not isinstance(cart_id, str) or not isinstance(item_id, int) or not isinstance(count, int):
            return jsonify({"error": "Invalid request"}), 400

        with get_db_connection() as conn:
            # Parameterized query to prevent SQL injection
            cart = conn.execute('SELECT 1 FROM carts WHERE cart_id = ?', (cart_id,)).fetchone()
            if not cart:
                return jsonify({"error": "Cart not found"}), 404

            # Parameterized query to prevent SQL injection
            row = conn.execute('SELECT count FROM cart_items WHERE cart_id = ? AND item_id = ?', 
                               (cart_id, item_id)).fetchone()
            
            current_count = row['count'] if row else 0
            new_count = current_count + count

            if new_count <= 0:
                conn.execute('DELETE FROM cart_items WHERE cart_id = ? AND item_id = ?', (cart_id, item_id))
            else:
                # Parameterized query to prevent SQL injection
                conn.execute('''
                    INSERT INTO cart_items (cart_id, item_id, count) 
                    VALUES (?, ?, ?) 
                    ON CONFLICT(cart_id, item_id) DO UPDATE SET count = excluded.count
                ''', (cart_id, item_id, new_count))
            
            conn.commit()

        return jsonify({"status": "success"}), 200
    except Exception:
        # Generic error to avoid leaking stack traces
        return jsonify({"error": "Internal server error"}), 500

@app.route('/retrieve_cart', methods=['POST'])
def retrieve_cart():
    try:
        data = request.get_json(silent=True)
        if data is None or 'cart_id' not in data:
            return jsonify({"error": "Invalid request"}), 400

        cart_id = data['cart_id']
        
        # Type validation
        if not isinstance(cart_id, str):
            return jsonify({"error": "Invalid request"}), 400

        with get_db_connection() as conn:
            # Parameterized query to prevent SQL injection
            cart = conn.execute('SELECT 1 FROM carts WHERE cart_id = ?', (cart_id,)).fetchone()
            if not cart:
                return jsonify({"error": "Cart not found"}), 404

            # Parameterized query to prevent SQL injection
            rows = conn.execute('SELECT item_id, count FROM cart_items WHERE cart_id = ?', (cart_id,)).fetchall()
            items = [{"item_id": row['item_id'], "count": row['count']} for row in rows]

        return jsonify({"items": items}), 200
    except Exception:
        # Generic error to avoid leaking stack traces
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    init_db()
    # Running on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)