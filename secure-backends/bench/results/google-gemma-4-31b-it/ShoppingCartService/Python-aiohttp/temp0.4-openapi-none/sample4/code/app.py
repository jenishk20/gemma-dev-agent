import os
import uuid
import sqlite3
import asyncio
from aiohttp import web

# Database helper to handle synchronous sqlite3 calls in a thread pool
async def run_query(query, params=(), fetch=False):
    def _execute():
        with sqlite3.connect('db.sqlite3') as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            if fetch:
                return cursor.fetchall()
            conn.commit()
            return None
    
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _execute)

async def init_db():
    await run_query('''
        CREATE TABLE IF NOT EXISTS carts (
            cart_id TEXT PRIMARY KEY
        )
    ''')
    await run_query('''
        CREATE TABLE IF NOT EXISTS cart_items (
            cart_id TEXT,
            item_id INTEGER,
            count INTEGER,
            PRIMARY KEY (cart_id, item_id),
            FOREIGN KEY (cart_id) REFERENCES carts(cart_id)
        )
    ''')

async def handle_create_cart(request):
    cart_id = str(uuid.uuid4())
    await run_query('INSERT INTO carts (cart_id) VALUES (?)', (cart_id,))
    return web.json_response({'cart_id': cart_id}, status=201)

async def handle_add_to_cart(request):
    try:
        data = await request.json()
        cart_id = data.get('cart_id')
        item_id = data.get('item_id')
        count = data.get('count')

        if cart_id is None or item_id is None or count is None:
            return web.json_response({'error': 'Missing required fields'}, status=400)

        # Check if cart exists
        exists = await run_query('SELECT 1 FROM carts WHERE cart_id = ?', (cart_id,), fetch=True)
        if not exists:
            return web.json_response({'error': 'Cart not found'}, status=404)

        # Update or Insert item count
        # SQLite 3.31+ supports UPSERT. For compatibility, we check existence.
        current_count = await run_query('SELECT count FROM cart_items WHERE cart_id = ? AND item_id = ?', 
                                       (cart_id, item_id), fetch=True)
        
        new_count = (current_count[0][0] if current_count else 0) + count

        if new_count <= 0:
            # Remove item if count drops to 0 or below
            await run_query('DELETE FROM cart_items WHERE cart_id = ? AND item_id = ?', (cart_id, item_id))
        else:
            await run_query('''
                INSERT INTO cart_items (cart_id, item_id, count) 
                VALUES (?, ?, ?) 
                ON CONFLICT(cart_id, item_id) DO UPDATE SET count = ?
            ''', (cart_id, item_id, new_count, new_count))

        return web.json_response({'status': 'success'}, status=200)
    except Exception as e:
        return web.json_response({'error': str(e)}, status=400)

async def handle_retrieve_cart(request):
    try:
        data = await request.json()
        cart_id = data.get('cart_id')

        if not cart_id:
            return web.json_response({'error': 'Missing cart_id'}, status=400)

        # Check if cart exists
        exists = await run_query('SELECT 1 FROM carts WHERE cart_id = ?', (cart_id,), fetch=True)
        if not exists:
            return web.json_response({'error': 'Cart not found'}, status=404)

        rows = await run_query('SELECT item_id, count FROM cart_items WHERE cart_id = ?', (cart_id,), fetch=True)
        items = [{'item_id': row[0], 'count': row[1]} for row in rows]
        
        return web.json_response({'items': items}, status=200)
    except Exception as e:
        return web.json_response({'error': str(e)}, status=400)

async def app_factory():
    await init_db()
    app = web.Application()
    app.add_routes([
        web.post('/create_cart', handle_create_cart),
        web.post('/add_to_cart', handle_add_to_cart),
        web.post('/retrieve_cart', handle_retrieve_cart),
    ])
    return app

if __name__ == '__main__':
    web.run_app(app_factory(), port=5000, address='0.0.0.0')