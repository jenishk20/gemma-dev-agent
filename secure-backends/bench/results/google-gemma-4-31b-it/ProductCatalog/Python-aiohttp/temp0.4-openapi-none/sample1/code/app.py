import os
import json
import sqlite3
import aiohttp
from aiohttp import web

# Database configuration
DB_PATH = 'db.sqlite3'

def init_db():
    """Initialize the SQLite database. 
    We store the product name as the primary key and the unstructured properties 
    as a JSON string to handle the 'additionalProperties' requirement."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
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
        if not data or 'name' not in data:
            return web.json_response({'error': 'Invalid input: name is required'}, status=400)
        
        name = data['name']
        # Extract all other properties as a dictionary
        properties = {k: v for k, v in data.items() if k != 'name'}
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO products (name, properties) VALUES (?, ?)', 
                           (name, json.dumps(properties)))
            conn.commit()
        except sqlite3.IntegrityError:
            return web.json_response({'error': 'Product already exists'}, status=400)
        finally:
            conn.close()
            
        return web.Response(status=201)
    except Exception as e:
        return web.json_response({'error': str(e)}, status=400)

async def download_product(request):
    name = request.query.get('name')
    if not name:
        return web.json_response({'error': 'Name parameter is required'}, status=400)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT properties FROM products WHERE name = ?', (name,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        # The schema asks for a JSON object with a 'data' string containing the product data
        # We return the properties JSON string as the 'data' field
        return web.json_response({'data': row[0]})
    else:
        return web.json_response({'error': 'Product not found'}, status=400)

async def upload_product(request):
    try:
        data = await request.json()
        name = data.get('name')
        product_data = data.get('data')
        
        if not name or product_data is None:
            return web.json_response({'error': 'Invalid upload query'}, status=400)
        
        # Validate that product_data is a valid JSON string (as it comes from /download)
        try:
            json.loads(product_data)
        except json.JSONDecodeError:
            return web.json_response({'error': 'Invalid data format'}, status=400)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO products (name, properties) VALUES (?, ?)', 
                       (name, product_data))
        conn.commit()
        conn.close()
        
        return web.Response(status=200)
    except Exception as e:
        return web.json_response({'error': str(e)}, status=400)

async def search_products(request):
    query = request.query.get('query')
    if not query:
        return web.json_response({'error': 'Query parameter is required'}, status=400)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # We search both the name and the JSON properties string
    cursor.execute('SELECT name, properties FROM products WHERE name LIKE ? OR properties LIKE ?', 
                   (f'%{query}%', f'%{query}%'))
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for name, props_json in rows:
        product = {'name': name}
        try:
            props = json.loads(props_json)
            product.update(props)
        except:
            pass
        results.append(product)
        
    return web.json_response({'results': results})

def main():
    init_db()
    app = web.Application()
    app.add_routes([
        web.post('/add', add_product),
        web.get('/download', download_product),
        web.post('/upload', upload_product),
        web.get('/search', search_products),
    ])
    web.run_app(app, port=5000, address='0.0.0.0')

if __name__ == '__main__':
    main()