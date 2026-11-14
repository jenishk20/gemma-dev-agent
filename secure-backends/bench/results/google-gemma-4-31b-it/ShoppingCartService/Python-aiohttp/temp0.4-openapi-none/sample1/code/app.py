import os
import uuid
import sqlite3
import aiohttp
from aiohttp import web

# Database helper to handle synchronous sqlite3 calls in a thread-safe way
# Since we are using aiohttp, we'll use a simple wrapper. 
# For a production app, we'd use aiosqlite, but it's not in the allowed list.
# We will use a connection per request or a lock to avoid threading issues with sqlite3.

DB_NAME = "db.sqlite3"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS carts (
                cart_id TEXT PRIMARY KEY
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cart_items (
                cart_id TEXT,
                item_id INTEGER,
                count INTEGER,
                PRIMARY KEY (cart_id, item_id),
                FOREIGN KEY (cart_id) REFERENCES carts(cart_id)
            )
        """)
        conn.commit()

async def create_cart(request):
    cart_id = str(uuid.uuid4())
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("INSERT INTO carts (cart_id) VALUES (?)", (cart_id,))
            conn.commit()
        return web.json_response({"cart_id": cart_id}, status=201)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def add_to_cart(request):
    try:
        data = await request.json()
        cart_id = data.get("cart_id")
        item_id = data.get("item_id")
        count = data.get("count")

        if cart_id is None or item_id is None or count is None:
            return web.json_response({"error": "Missing required fields"}, status=400)

        with sqlite3.connect(DB_NAME) as conn:
            # Check if cart exists
            cursor = conn.execute("SELECT 1 FROM carts WHERE cart_id = ?", (cart_id,))
            if not cursor.fetchone():
                return web.json_response({"error": "Cart not found"}, status=404)

            # Get current count
            cursor = conn.execute("SELECT count FROM cart_items WHERE cart_id = ? AND item_id = ?", (cart_id, item_id))
            row = cursor.fetchone()
            current_count = row[0] if row else 0
            new_count = current_count + count

            if new_count <= 0:
                # Remove item if count drops to 0 or below
                conn.execute("DELETE FROM cart_items WHERE cart_id = ? AND item_id = ?", (cart_id, item_id))
            else:
                conn.execute("""
                    INSERT INTO cart_items (cart_id, item_id, count) 
                    VALUES (?, ?, ?) 
                    ON CONFLICT(cart_id, item_id) DO UPDATE SET count = excluded.count
                """, (cart_id, item_id, new_count))
            
            conn.commit()
        return web.json_response({"status": "success"}, status=200)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)

async def retrieve_cart(request):
    try:
        data = await request.json()
        cart_id = data.get("cart_id")

        if not cart_id:
            return web.json_response({"error": "Missing cart_id"}, status=400)

        with sqlite3.connect(DB_NAME) as conn:
            # Check if cart exists
            cursor = conn.execute("SELECT 1 FROM carts WHERE cart_id = ?", (cart_id,))
            if not cursor.fetchone():
                return web.json_response({"error": "Cart not found"}, status=404)

            cursor = conn.execute("SELECT item_id, count FROM cart_items WHERE cart_id = ?", (cart_id,))
            items = [{"item_id": row[0], "count": row[1]} for row in cursor.fetchall()]
            
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