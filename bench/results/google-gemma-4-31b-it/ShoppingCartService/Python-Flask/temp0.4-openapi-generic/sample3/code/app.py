import os
import sqlite3
import uuid
from flask import Flask, request, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key")

DB_FILE = "db.sqlite3"

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
                FOREIGN KEY (cart_id REFERENCES carts(cart_id))
            )
        ''')
        conn.commit()

@app.route('/create_cart', methods=['POST'])
def create_cart():
    cart_id = str(uuid.uuid4())
    try:
        with get_db_connection() as conn:
            conn.execute('INSERT INTO carts (cart_id) VALUES (?)', (cart_id,))
            conn.commit()
        return jsonify({"cart_id": cart_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing request body"}), 400

    cart_id = data.get('cart_id')
    item_id = data.get('item_id')
    count = data.get('count')

    if cart_id is None or item_id is None or count is None:
        return jsonify({"error": "Invalid request: cart_id, item_id, and count are required"}), 400

    if not isinstance(item_id, int) or not isinstance(count, int):
        return jsonify({"error": "item_id and count must be integers"}), 400

    try:
        with get_db_connection() as conn:
            # Check if cart exists
            cart = conn.execute('SELECT 1 FROM carts WHERE cart_id = ?', (cart_id,)).fetchone()
            if not cart:
                return jsonify({"error": "Cart not found"}), 404

            # Update or Insert item count
            # Using UPSERT logic (SQLite 3.24+)
            conn.execute('''
                INSERT INTO cart_items (cart_id, item_id, count) 
                VALUES (?, ?, ?) 
                ON CONFLICT(cart_id, item_id) DO UPDATE SET count = count + excluded.count
            ''', (cart_id, item_id, count))
            
            # Remove item if count becomes 0 or negative
            conn.execute('DELETE FROM cart_items WHERE cart_id = ? AND count <= 0', (cart_id,))
            
            conn.commit()
        return jsonify({"message": "Item added or removed successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/retrieve_cart', methods=['POST'])
def retrieve_cart():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing request body"}), 400

    cart_id = data.get('cart_id')
    if cart_id is None:
        return jsonify({"error": "cart_id is required"}), 400

    try:
        with get_db_connection() as conn:
            # Check if cart exists
            cart = conn.execute('SELECT 1 FROM carts WHERE cart_id = ?', (cart_id,)).fetchone()
            if not cart:
                return jsonify({"error": "Cart not found"}), 404

            items_rows = conn.execute('SELECT item_id, count FROM cart_items WHERE cart_id = ?', (cart_id,)).fetchall()
            
            items = [{"item_id": row['item_id'], "count": row['count']} for row in items_rows]
            return jsonify({"items": items}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)