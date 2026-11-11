import os
import json
import sqlite3
from aiohttp import web

# Database initialization
DB_NAME = "db.sqlite3"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        # We store products in a table. 
        # Since properties are unstructured, we store the 'name' as a primary key 
        # and the rest of the properties as a JSON string.
        conn.execute(
            "CREATE TABLE IF NOT EXISTS products (name TEXT PRIMARY KEY, data TEXT)"
        )
        conn.commit()

async def handle_add(request):
    try:
        body = await request.json()
    except Exception:
        return web.response.json({"error": "Invalid JSON"}, status=400)

    if not body or not isinstance(body, dict) or "name" not in body:
        return web.response.json({"error": "Missing required field: name"}, status=400)

    name = body["name"]
    # Filter out 'name' to store only the additional properties
    properties = {k: v for k, v in body.items() if k != "name"}
    
    # Ensure all additional properties are strings as per schema
    for k, v in properties.items():
        if not isinstance(v, str):
            return web.response.json({"error": f"Property {k} must be a string"}, status=400)

    try:
        with sqlite3.connect(DB_NAME) as conn:
            # Use REPLACE to handle updates if the name already exists, 
            # though the schema implies /add is for new products.
            conn.execute(
                "INSERT OR REPLACE INTO products (name, data) VALUES (?, ?)",
                (name, json.dumps(properties))
            )
            conn.commit()
    except Exception as e:
        return web.response.json({"error": str(e)}, status=500)

    return web.Response(status=201)

async def handle_download(request):
    name = request.query.get("name")
    if not name:
        return web.response.json({"error": "Missing query parameter: name"}, status=400)

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute("SELECT data FROM products WHERE name = ?", (name,))
        row = cursor.fetchone()

    if row:
        # The schema says /download returns an object with a 'data' string property.
        # The 'data' string represents the unstructured properties.
        return web.response.json({"data": row[0]})
    else:
        return web.response.json({"error": "Product not found"}, status=404)

async def handle_upload(request):
    try:
        body = await request.json()
    except Exception:
        return web.response.json({"error": "Invalid JSON"}, status=400)

    if not body or not isinstance(body, dict) or "name" not in body or "data" not in body:
        return web.response.json({"error": "Invalid upload query"}, status=400)

    name = body["name"]
    data_str = body["data"]

    # Validate that data_str is a valid JSON string (since it comes from /download)
    try:
        json.loads(data_str)
    except Exception:
        return web.response.json({"error": "Invalid data format"}, status=400)

    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO products (name, data) VALUES (?, ?)",
                (name, data_str)
            )
            conn.commit()
    except Exception as e:
        return web.response.json({"error": str(e)}, status=500)

    return web.Response(status=200)

async def handle_search(request):
    query = request.query.get("query")
    if not query:
        return web.response.json({"error": "Missing query parameter: query"}, status=400)

    results = []
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute("SELECT name, data FROM products")
        rows = cursor.fetchall()

    for name, data_json in rows:
        properties = json.loads(data_json)
        # Search in name or any of the values of the unstructured properties
        match = (query.lower() in name.lower()) or any(
            query.lower() in str(v).lower() for v in properties.values()
        )
        if match:
            product = {"name": name}
            product.update(properties)
            results.append(product)

    return web.response.json({"results": results})

def main():
    init_db()
    app = web.Application()
    app.add_routes([
        web.post('/add', handle_add),
        web.get('/download', handle_download),
        web.post('/upload', handle_upload),
        web.get('/search', handle_search),
    ])
    web.run_app(app, host='0.0.0.0', port=5000)

if __name__ == "__main__":
    main()