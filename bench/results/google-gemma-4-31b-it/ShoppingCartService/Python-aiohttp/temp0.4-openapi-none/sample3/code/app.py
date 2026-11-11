import os
import sqlite3
import uuid
import json
from aiohttp import web

DB_NAME = "db.sqlite3"

def init_db():
    """Initialize the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Create carts table to store cart existence
    cursor.execute("CREATE TABLE IF NOT EXISTS carts (cart_id TEXT PRIMARY KEY)")
    # Create cart_items table to store items and their counts
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cart_items (
            cart_id TEXT,
            item_id INTEGER,
            count INTEGER,
            PRIMARY KEY (cart_id, item_id),
            FOREIGN KEY (cart_id) REFERENCES carts(cart_id)
        )
    """)
    conn.commit()
    conn.close()

async def create_cart(request):
    """POST /create_cart"""
    cart_id = str(uuid.uuid4())
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO carts (cart_id) VALUES (?)", (cart_id,))
    conn.commit()
    conn.close()
    return web.json_response({"cart_id": cart_id}, status=201)

async def add_to_cart(request):
    """POST /add_to_cart"""
    try:
        data = await request.json()
        cart_id = data.get("cart_id")
        item_id = data.get("item_id")
        count = data.get("count")

        if cart_id is None or item_id is None or count is None:
            return web.json_response({"error": "Missing required fields"}, status=400)

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Check if cart exists
        cursor.execute("SELECT 1 FROM carts WHERE cart_id = ?", (cart_id,))
        if not cursor.fetchone():
            conn.close()
            return web.json_response({"error": "Cart not found"}, status=404)

        # Get current count
        cursor.execute("SELECT count FROM cart_items WHERE cart_id = ? AND item_id = ?", (cart_id, item_id))
        row = cursor.fetchone()
        current_count = row[0] if row else 0
        new_count = current_count + count

        if new_count <= 0:
            # Remove item if count drops to 0 or below
            cursor.execute("DELETE FROM cart_items WHERE cart_id = ? AND item_id = ?", (cart_id, item_id))
        else:
            # Update or Insert
            cursor.execute("""
                INSERT INTO cart_items (cart_id, item_id, count) 
                VALUES (?, ?, ?) 
                ON CONFLICT(cart_id, item_id) DO UPDATE SET count = ?
            """, (cart_id, item_id, new_count, new_count))

        conn.commit()
        conn.close()
        return web.json_response({"status": "success"}, status=200)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)

async def retrieve_cart(request):
    """POST /retrieve_cart"""
    try:
        data = await request.json()
        cart_id = data.get("cart_id")

        if cart_id is None:
            return web.json_response({"error": "cart_id is required"}, status=400)

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Check if cart exists
        cursor.execute("SELECT 1 FROM carts WHERE cart_id = ?", (cart_id,))
        if not cursor.fetchone():
            conn.close()
            return web.json_response({"error": "Cart not found"}, status=404)

        # Get items
        cursor.execute("SELECT item_id, count FROM cart_items WHERE cart_id = ?", (cart_id,))
        rows = cursor.fetchall()
        conn.close()

        items = [{"item_id": row[0], "count": row[1]} for row in rows]
        return web.json_response({"items": items}, status=200)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)

app = web.Application()
app.add_routes([
    web.post('/create_cart', create_cart),
    web.post('/add_to_cart', add_to_cart),
    web.post('/retrieve_cart', retrieve_cart),
])

if __name__ == "__main__":
    init_db()
    web.run_app(app, host='0.0.0.0', port=5000)