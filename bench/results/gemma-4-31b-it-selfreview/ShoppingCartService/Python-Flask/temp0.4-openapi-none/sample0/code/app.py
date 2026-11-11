import os
import sqlite3
import uuid
from flask import Flask, request, jsonify

app = Flask(__name__)
# Use the provided APP_SECRET env variable
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key")

DB_FILE = "db.sqlite3"

# Resource exhaustion: Limit the size of the request body to prevent memory exhaustion
# Flask's MAX_CONTENT_LENGTH can be set to prevent large payloads
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1MB limit

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # Create carts table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS carts (
                cart_id TEXT PRIMARY KEY
            )
        ''')
        # Create cart_items table
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

@app.route('/create_cart', methods=['POST'])
def create_cart():
    try:
        cart_id = str(uuid.uuid4())
        with get_db_connection() as conn:
            # Parameterized query prevents SQL injection
            conn.execute('INSERT INTO carts (cart_id) VALUES (?)', (cart_id,))
            conn.commit()
        return jsonify({"cart_id": cart_id}), 201
    except Exception:
        # Error handling: return generic error to avoid leaking internal details
        return jsonify({"error": "Internal server error"}), 500

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    try:
        # Ensure the request is JSON
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Invalid request"}), 400
        
        cart_id = data.get('cart_id')
        item_id = data.get('item_id')
        count = data.get('count')

        # Validate types and presence of required fields
        if not isinstance(cart_id, str) or not isinstance(item_id, int) or not isinstance(count, int):
            return jsonify({"error": "Invalid request"}), 400

        with get_db_connection() as conn:
            # Parameterized query prevents SQL injection
            cursor = conn.execute('SELECT 1 FROM carts WHERE cart_id = ?', (cart_id,))
            if not cursor.fetchone():
                return jsonify({"error": "Cart not found"}), 404

            # Parameterized query prevents SQL injection
            cursor = conn.execute('SELECT count FROM cart_items WHERE cart_id = ? AND item_id = ?', (cart_id, item_id))
            row = cursor.fetchone()
            
            if row:
                new_count = row['count'] + count
                if new_count <= 0:
                    conn.execute('DELETE FROM cart_items WHERE cart_id = ? AND item_id = ?', (cart_id, item_id))
                else:
                    conn.execute('UPDATE cart_items SET count = ? WHERE cart_id = ? AND item_id = ?', (new_count, cart_id, item_id))
            else:
                if count > 0:
                    conn.execute('INSERT INTO cart_items (cart_id, item_id, count) VALUES (?, ?, ?)', (cart_id, item_id, count))
            
            conn.commit()
        
        return jsonify({"status": "success"}), 200
    except Exception:
        return jsonify({"error": "Internal server error"}), 500

@app.route('/retrieve_cart', methods=['POST'])
def retrieve_cart():
    try:
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Invalid request"}), 400
        
        cart_id = data.get('cart_id')
        if not isinstance(cart_id, str):
            return jsonify({"error": "Invalid request"}), 400

        with get_db_connection() as conn:
            # Parameterized query prevents SQL injection
            cursor = conn.execute('SELECT 1 FROM carts WHERE cart_id = ?', (cart_id,))
            if not cursor.fetchone():
                return jsonify({"error": "Cart not found"}), 404

            # Parameterized query prevents SQL injection
            cursor = conn.execute('SELECT item_id, count FROM cart_items WHERE cart_id = ?', (cart_id,))
            items = [{"item_id": row['item_id'], "count": row['count']} for row in cursor.fetchall()]
        
        return jsonify({"items": items}), 200
    except Exception:
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    init_db()
    # Port 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)