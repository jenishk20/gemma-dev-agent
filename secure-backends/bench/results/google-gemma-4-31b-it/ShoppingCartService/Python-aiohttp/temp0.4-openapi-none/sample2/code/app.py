import os
import uuid
import sqlite3
import aiohttp
from aiohttp import web

# Database helper to handle synchronous sqlite3 calls in an async environment
# Since we are using standard sqlite3, we wrap it in a simple class.
# In a production environment, aiosqlite would be preferred.
class Database:
    def __init__(self, db_path="db.sqlite3"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
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
                    FOREIGN KEY (cart_id) REFERENCES carts (cart_id)
                )
            """)
            conn.commit()

    def create_cart(self):
        cart_id = str(uuid.uuid4())
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO carts (cart_id) VALUES (?)", (cart_id,))
            conn.commit()
        return cart_id

    def add_to_cart(self, cart_id, item_id, count):
        with sqlite3.connect(self.db_path) as conn:
            # Check if cart exists
            cursor = conn.execute("SELECT 1 FROM carts WHERE cart_id = ?", (cart_id,))
            if not cursor.fetchone():
                return False
            
            # Upsert logic for item count
            cursor = conn.execute("SELECT count FROM cart_items WHERE cart_id = ? AND item_id = ?", (cart_id, item_id))
            row = cursor.fetchone()
            
            if row:
                new_count = row[0] + count
                if new_count <= 0:
                    conn.execute("DELETE FROM cart_items WHERE cart_id = ? AND item_id = ?", (cart_id, item_id))
                else:
                    conn.execute("UPDATE cart_items SET count = ? WHERE cart_id = ? AND item_id = ?", (new_count, cart_id, item_id))
            else:
                if count > 0:
                    conn.execute("INSERT INTO cart_items (cart_id, item_id, count) VALUES (?, ?, ?)", (cart_id, item_id, count))
            
            conn.commit()
            return True

    def get_cart(self, cart_id):
        with sqlite3.connect(self.db_path) as conn:
            # Check if cart exists
            cursor = conn.execute("SELECT 1 FROM carts WHERE cart_id = ?", (cart_id,))
            if not cursor.fetchone():
                return None
            
            cursor = conn.execute("SELECT item_id, count FROM cart_items WHERE cart_id = ?", (cart_id,))
            items = [{"item_id": row[0], "count": row[1]} for row in cursor.fetchall()]
            return items

db = Database()

async def handle_create_cart(request):
    cart_id = db.create_cart()
    return web.json_response({"cart_id": cart_id}, status=201)

async def handle_add_to_cart(request):
    try:
        data = await request.json()
        cart_id = data.get("cart_id")
        item_id = data.get("item_id")
        count = data.get("count")

        if cart_id is None or item_id is None or count is None:
            return web.json_response({"error": "Invalid request"}, status=400)

        success = db.add_to_cart(str(cart_id), int(item_id), int(count))
        if not success:
            return web.json_response({"error": "Cart not found"}, status=404)

        return web.json_response({}, status=200)
    except (ValueError, TypeError, json.JSONDecodeError):
        return web.json_response({"error": "Invalid request"}, status=400)
    except Exception:
        return web.json_response({"error": "Internal Server Error"}, status=500)

async def handle_retrieve_cart(request):
    try:
        data = await request.json()
        cart_id = data.get("cart_id")

        if cart_id is None:
            return web.json_response({"error": "Invalid request"}, status=400)

        items = db.get_cart(str(cart_id))
        if items is None:
            return web.json_response({"error": "Cart not found"}, status=404)

        return web.json_response({"items": items}, status=200)
    except Exception:
        return web.json_response({"error": "Invalid request"}, status=400)

# Import json here to handle potential decode errors in the handlers
import json

app = web.Application()
app.add_routes([
    web.post('/create_cart', handle_create_cart),
    web.post('/add_to_cart', handle_add_to_cart),
    web.post('/retrieve_cart', handle_retrieve_cart),
])

if __name__ == '__main__':
    web.run_app(app, host='0.0.0.0', port=5000)