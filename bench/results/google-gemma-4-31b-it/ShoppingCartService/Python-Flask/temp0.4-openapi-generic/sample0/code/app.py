import os
import sqlite3
import uuid
from flask import Flask, request, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default_secret_for_dev")

DB_FILE = "db.sqlite3"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # Create carts table to store the existence of a cart
        conn.execute('''
            CREATE TABLE IF NOT EXISTS carts (
                cart_id TEXT PRIMARY KEY
            )
        ''')
        # Create cart_items table to store items and their quantities
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
    cart_id = str(uuid.uuid4())
    try:
        with get_db_connection() as conn:
            conn.execute('INSERT INTO carts (cart_id) VALUES (?)', (cart_id,))
            conn.commit()
        return jsonify({"cart_id": cart_id}), 201
    except sqlite3.Error:
        return jsonify({"error": "Could not create cart"}), 500

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing request body"}), 400

    cart_id = data.get('cart_id')
    item_id = data.get('item_id')
    count = data.get('count')

    if cart_id is None or item_id is None or count is None:
        return jsonify({"error": "Missing required fields: cart_id, item_id, count"}), 400

    if not isinstance(item_id, int) or not isinstance(count, int):
        return jsonify({"error": "item_id and count must be integers"}), 400

    try:
        with get_db_connection() as conn:
            # Check if cart exists
            cursor = conn.execute('SELECT 1 FROM carts WHERE cart_id = ?', (cart_id,))
            if not cursor.fetchone():
                return jsonify({"error": "Cart not found"}), 404

            # Update or insert item count
            # Use UPSERT logic (INSERT OR REPLACE or manual check)
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
                else:
                    # If count is negative and item doesn't exist, we do nothing or return error. 
                    # Based on typical cart behavior, we just don't add it.
                    pass
            conn.commit()
        return jsonify({"message": "Item updated successfully"}), 200
    except sqlite3.Error:
        return jsonify({"error": "Database error"}), 500

@app.route('/retrieve_cart', methods=['POST'])
def retrieve_cart():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing request body"}), 400

    cart_id = data.get('cart_id')
    if cart_id is None:
        return jsonify({"error": "Missing required field: cart_id"}), 400

    try:
        with get_db_connection() as conn:
            # Check if cart exists
            cursor = conn.execute('SELECT 1 FROM carts WHERE cart_id = ?', (cart_id,))
            if not cursor.fetchone():
                return jsonify({"error": "Cart not found"}), 404

            # Get all items
            cursor = conn.execute('SELECT item_id, count FROM cart_items WHERE cart_id = ?', (cart_id,))
            items = [{"item_id": row['item_id'], "count": row['count']} for row in cursor.fetchall()]
            
        return jsonify({"items": items}), 200
    except sqlite3.Error:
        return jsonify({"error": "Database error"}), 500

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)