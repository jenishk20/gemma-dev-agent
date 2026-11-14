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
                FOREIGN KEY (cart_id REFERENCES carts(cart_id))
            )
        ''')
        conn.commit()

@app.route('/create_cart', methods=['POST'])
def create_cart():
    cart_id = str(uuid.uuid4())
    with get_db_connection() as conn:
        conn.execute('INSERT INTO carts (cart_id) VALUES (?)', (cart_id,))
        conn.commit()
    return jsonify({"cart_id": cart_id}), 201

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    data = request.get_json()
    if not data or not all(k in data for k in ('cart_id', 'item_id', 'count')):
        return jsonify({"error": "Invalid request"}), 400

    cart_id = data['cart_id']
    item_id = data['item_id']
    count = data['count']

    with get_db_connection() as conn:
        # Check if cart exists
        cart = conn.execute('SELECT 1 FROM carts WHERE cart_id = ?', (cart_id,)).fetchone()
        if not cart:
            return jsonify({"error": "Cart not found"}), 404

        # Get current count
        row = conn.execute('SELECT count FROM cart_items WHERE cart_id = ? AND item_id = ?', 
                           (cart_id, item_id)).fetchone()
        
        current_count = row['count'] if row else 0
        new_count = current_count + count

        if new_count <= 0:
            # Remove item if count drops to 0 or below
            conn.execute('DELETE FROM cart_items WHERE cart_id = ? AND item_id = ?', 
                         (cart_id, item_id))
        else:
            # Update or Insert
            conn.execute('''
                INSERT INTO cart_items (cart_id, item_id, count) 
                VALUES (?, ?, ?) 
                ON CONFLICT(cart_id, item_id) DO UPDATE SET count = ?
            ''', (cart_id, item_id, new_count, new_count))
        
        conn.commit()
    
    return jsonify({"status": "success"}), 200

@app.route('/retrieve_cart', methods=['POST'])
def retrieve_cart():
    data = request.get_json()
    if not data or 'cart_id' not in data:
        return jsonify({"error": "Invalid request"}), 400

    cart_id = data['cart_id']

    with get_db_connection() as conn:
        # Check if cart exists
        cart = conn.execute('SELECT 1 FROM carts WHERE cart_id = ?', (cart_id,)).fetchone()
        if not cart:
            return jsonify({"error": "Cart not found"}), 404

        items_rows = conn.execute('SELECT item_id, count FROM cart_items WHERE cart_id = ?', 
                                  (cart_id,)).fetchall()
        
        items = [{"item_id": row['item_id'], "count": row['count']} for row in items_rows]
    
    return jsonify({"items": items}), 200

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)