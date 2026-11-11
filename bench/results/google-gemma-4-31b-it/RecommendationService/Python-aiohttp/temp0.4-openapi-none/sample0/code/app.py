import os
import sqlite3
import asyncio
from aiohttp import web

# Database initialization
DB_PATH = "db.sqlite3"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Create products table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    ''')
    # Create tags table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            product_id INTEGER,
            tag TEXT NOT NULL,
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    ''')
    conn.commit()
    conn.close()

async def get_db_connection():
    # Using a synchronous sqlite3 connection in a thread pool via loop.run_in_executor 
    # is the standard way to handle sqlite3 with aiohttp since sqlite3 is blocking.
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

async def handle_recommender_get(request):
    tags_query = request.query.get('tags')
    if not tags_query:
        return web.Response(text="Missing tags parameter", status=400)

    # Split tags by comma and clean whitespace
    search_tags = [t.strip() for t in tags_query.split(',') if t.strip()]
    if not search_tags:
        return web.Response(text="No valid tags provided", status=400)

    loop = asyncio.get_event_loop()
    def fetch_products():
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Find products that match at least one of the tags
        placeholders = ','.join(['?'] * len(search_tags))
        query = f'''
            SELECT DISTINCT p.name 
            FROM products p 
            JOIN tags t ON p.id = t.product_id 
            WHERE t.tag IN ({placeholders})
        '''
        cursor.execute(query, search_tags)
        results = cursor.fetchall()
        conn.close()
        return results

    products = await loop.run_in_executor(None, fetch_products)
    
    # Generate HTML response
    html_content = "<html><body><h1>Recommended Products</h1><ul>"
    if not products:
        html_content += "<li>No products found matching those tags.</li>"
    else:
        for row in products:
            name = row[0]
            html_content += f"<li>{name}</li>"
    html_content += "</ul></body></html>"
    
    return web.Response(text=html_content, content_type='text/html')

async def handle_recommender_post(request):
    try:
        data = await request.json()
    except Exception:
        return web.Response(text="Invalid JSON", status=400)

    product_name = data.get('product_name')
    tags = data.get('tags')

    if not product_name or not isinstance(tags, list):
        return web.Response(text="Invalid input: product_name (string) and tags (list) required", status=400)

    loop = asyncio.get_event_loop()
    def save_product():
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO products (name) VALUES (?)", (product_name,))
        product_id = cursor.lastrowid
        for tag in tags:
            if isinstance(tag, str):
                cursor.execute("INSERT INTO tags (product_id, tag) VALUES (?, ?)", (product_id, tag))
        conn.commit()
        conn.close()

    await loop.run_in_executor(None, save_product)
    return web.Response(text="Successful operation", status=200)

async def init_app():
    app = web.Application()
    app.add_routes([
        web.get('/recommender', handle_recommender_get),
        web.post('/recommender', handle_recommender_post),
    ])
    return app

if __name__ == '__main__':
    init_db()
    app = asyncio.run(init_app()) # This is slightly wrong for aiohttp, usually we use web.run_app
    # Correcting to web.run_app
    web.run_app(app, host='0.0.0.0', port=5000)

# Re-writing the main block to be strictly correct for aiohttp
def start_server():
    init_db()
    app = web.Application()
    app.add_routes([
        web.get('/recommender', handle_recommender_get),
        web.post('/recommender', handle_recommender_post),
    ])
    web.run_app(app, port=5000)

# Since I need to put everything in one file and ensure it runs:
if __name__ == '__main__':
    start_server()