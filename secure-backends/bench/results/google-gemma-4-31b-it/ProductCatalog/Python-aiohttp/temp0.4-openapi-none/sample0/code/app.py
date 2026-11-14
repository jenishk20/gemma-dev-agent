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
    # The 'properties' column stores a JSON string of all additional properties.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            name TEXT PRIMARY KEY,
            properties TEXT
        )
    ''')
    conn.commit()
    conn.close()

async def handle_add(request):
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return web.response_json({"error": "Invalid JSON"}, status=400)

    if not data or 'name' not in data:
        return web.response_json({"error": "Missing required field: name"}, status=400)

    name = data['name']
    # Extract all other properties
    properties = {k: v for k, v in data.items() if k != 'name'}
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Using REPLACE to handle updates if name already exists, or just INSERT
        cursor.execute("INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)", 
                       (name, json.dumps(properties)))
        conn.commit()
        conn.close()
    except Exception as e:
        return web.response_json({"error": str(e)}, status=500)

    return web.Response(status=201)

async def handle_download(request):
    name = request.query.get('name')
    if not name:
        return web.response_json({"error": "Missing query parameter: name"}, status=400)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT properties FROM products WHERE name = ?", (name,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return web.response_json({"error": "Product not found"}, status=404)

    # The schema asks for the data as a string in a JSON object
    return web.response_json({"data": row[0]})

async def handle_upload(request):
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return web.response_json({"error": "Invalid JSON"}, status=400)

    if not data or 'name' not in data or 'data' not in data:
        return web.response_json({"error": "Invalid upload query"}, status=400)

    name = data['name']
    properties_json = data['data']

    # Validate that 'data' is a valid JSON string (since it represents the properties)
    try:
        json.loads(properties_json)
    except json.JSONDecodeError:
        return web.response_json({"error": "Data field must be a valid JSON string"}, status=400)

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)", 
                       (name, properties_json))
        conn.commit()
        conn.close()
    except Exception as e:
        return web.response_json({"error": str(e)}, status=500)

    return web.Response(status=200)

async def handle_search(request):
    query = request.query.get('query')
    if not query:
        return web.response_json({"error": "Missing query parameter: query"}, status=400)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, properties FROM products")
    rows = cursor.fetchall()
    conn.close()

    results = []
    for name, props_json in rows:
        props = json.loads(props_json)
        # Check if query matches name or any value in the unstructured properties
        match = (query.lower() in name.lower())
        if not match:
            for val in props.values():
                if isinstance(val, str) and query.lower() in val.lower():
                    match = True
                    break
        
        if match:
            product = {"name": name}
            product.update(props)
            results.append(product)

    return web.response_json({"results": results})

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