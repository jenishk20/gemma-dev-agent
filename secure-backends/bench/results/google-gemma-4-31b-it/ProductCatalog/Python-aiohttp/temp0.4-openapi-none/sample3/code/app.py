import os
import json
import sqlite3
import asyncio
from aiohttp import web

# Database initialization
DB_NAME = "db.sqlite3"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        # We store the product name as primary key and the unstructured properties as a JSON string
        conn.execute("CREATE TABLE IF NOT EXISTS products (name TEXT PRIMARY KEY, data TEXT)")
        conn.commit()

async def db_execute(query, params=(), fetch=False):
    """Helper to run sqlite queries in a thread pool to avoid blocking the event loop."""
    def sync_op():
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            if fetch:
                return [dict(row) for row in cursor.fetchall()]
            conn.commit()
            return None
    return await asyncio.to_thread(sync_op)

async def handle_add(request):
    try:
        body = await request.json()
        if not body or 'name' not in body:
            return web.json_response({"error": "Missing required field: name"}, status=400)
        
        name = body['name']
        # Extract all other properties
        properties = {k: v for k, v in body.items() if k != 'name'}
        # Store the whole object as JSON for simplicity in unstructured storage
        data_json = json.dumps(body)
        
        try:
            await db_execute("INSERT INTO products (name, data) VALUES (?, ?)", (name, data_json))
        except sqlite3.IntegrityError:
            return web.json_response({"error": "Product already exists"}, status=400)
            
        return web.Response(status=201)
    except Exception:
        return web.json_response({"error": "Invalid input"}, status=400)

async def handle_download(request):
    name = request.query.get('name')
    if not name:
        return web.json_response({"error": "Missing name parameter"}, status=400)
    
    results = await db_execute("SELECT data FROM products WHERE name = ?", (name,), fetch=True)
    if not results:
        return web.json_response({"error": "Product not found"}, status=404)
    
    # The schema asks for the data of the product as a string in the 'data' field
    product_data = results[0]['data']
    return web.json_response({"data": product_data})

async def handle_upload(request):
    try:
        body = await request.json()
        if not body or 'name' not in body or 'data' not in body:
            return web.json_response({"error": "Invalid upload query"}, status=400)
        
        name = body['name']
        data_str = body['data']
        
        # Validate that data_str is actually valid JSON representing the product
        try:
            parsed = json.loads(data_str)
            if not isinstance(parsed, dict) or parsed.get('name') != name:
                return web.json_response({"error": "Data content does not match product name"}, status=400)
        except json.JSONDecodeError:
            return web.json_response({"error": "Invalid JSON data"}, status=400)

        await db_execute("INSERT OR REPLACE INTO products (name, data) VALUES (?, ?)", (name, data_str))
        return web.json_response({"message": "Product updated"}, status=200)
    except Exception:
        return web.json_response({"error": "Invalid upload query"}, status=400)

async def handle_search(request):
    query_str = request.query.get('query')
    if not query_str:
        return web.json_response({"error": "Missing query parameter"}, status=400)
    
    # Fetch all products and filter in Python because of unstructured JSON properties
    all_products = await db_execute("SELECT data FROM products", fetch=True)
    results = []
    
    for row in all_products:
        product = json.loads(row['data'])
        # Search in name or any value of the unstructured properties
        match = False
        for val in product.values():
            if isinstance(val, str) and query_str.lower() in val.lower():
                match = True
                break
        if match:
            results.append(product)
            
    return web.json_response({"results": results})

app = web.Application()
app.add_routes([
    web.post('/add', handle_add),
    web.get('/download', handle_download),
    web.post('/upload', handle_upload),
    web.get('/search', handle_search),
])

if __name__ == '__main__':
    init_db()
    web.run_app(app, host='0.0.0.0', port=5000)