import os
import json
import sqlite3
import aiohttp
from aiohttp import web

# Database initialization
DB_PATH = "db.sqlite3"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # We store the product name as the primary key.
    # The 'properties' column stores a JSON string of all additional unstructured properties.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            name TEXT PRIMARY KEY,
            properties TEXT
        )
    ''')
    conn.commit()
    conn.close()

async def add_product(request):
    try:
        data = await request.json()
    except Exception:
        return web.response_json({"error": "Invalid JSON"}, status=400)

    if not data or 'name' not in data:
        return web.response_json({"error": "Missing required field: name"}, status=400)

    name = data.pop('name')
    # All remaining fields are unstructured properties
    properties = json.dumps(data)

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO products (name, properties) VALUES (?, ?)', (name, properties))
        conn.commit()
        conn.close()
        return web.Response(status=201)
    except sqlite3.IntegrityError:
        return web.response_json({"error": "Product already exists"}, status=400)
    except Exception as e:
        return web.response_json({"error": str(e)}, status=400)

async def download_product(request):
    name = request.query.get('name')
    if not name:
        return web.response_json({"error": "Missing query parameter: name"}, status=400)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT properties FROM products WHERE name = ?', (name,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return web.response_json({"error": "Product not found"}, status=404)

    # The schema specifies returning a JSON object with a 'data' field containing the product data
    # Since the /upload endpoint expects the format returned by /download, 
    # we return the properties as a string (JSON representation).
    return web.json_response({"data": row[0]})

async def upload_product(request):
    try:
        data = await request.json()
    except Exception:
        return web.response_json({"error": "Invalid JSON"}, status=400)

    name = data.get('name')
    payload = data.get('data')

    if not name or payload is None:
        return web.response_json({"error": "Invalid upload query"}, status=400)

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Fully replaces previous data
        cursor.execute('INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)', (name, payload))
        conn.commit()
        conn.close()
        return web.Response(status=200)
    except Exception as e:
        return web.response_json({"error": str(e)}, status=400)

async def search_products(request):
    query = request.query.get('query')
    if not query:
        return web.response_json({"error": "Missing query parameter: query"}, status=400)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Search in name or within the JSON properties string
    cursor.execute('SELECT name, properties FROM products WHERE name LIKE ? OR properties LIKE ?', 
                   (f'%{query}%', f'%{query}%'))
    rows = cursor.fetchall()
    conn.close()

    results = []
    for name, props_json in rows:
        product = {"name": name}
        try:
            props = json.loads(props_json)
            product.update(props)
        except Exception:
            pass
        results.append(product)

    return web.json_response({"results": results})

async def app():
    init_db()
    app = web.Application()
    app.add_routes([
        web.post('/add', add_product),
        web.get('/download', download_product),
        web.post('/upload', upload_product),
        web.get('/search', search_products),
    ])
    return app

if __name__ == '__main__':
    web.run_app(app(), port=5000, address='0.0.0.0')