import os
import sqlite3
import json
from aiohttp import web

# Database initialization
DB_NAME = "db.sqlite3"

def init_db():
    conn = sqlite3.connect(DB_NAME)
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
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')
    conn.commit()
    conn.close()

def get_db_connection():
    return sqlite3.connect(DB_NAME)

async def handle_recommender_get(request):
    tags_query = request.query.get('tags')
    if not tags_query:
        return web.Response(text="Missing tags parameter", status=400)

    # Split tags by comma and clean whitespace
    search_tags = [t.strip() for t in tags_query.split(',') if t.strip()]
    
    if not search_tags:
        return web.Response(text="No valid tags provided", status=400)

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Query products that match at least one of the provided tags
    # Using placeholders to prevent SQL injection
    placeholders = ','.join(['?'] * len(search_tags))
    query = f'''
        SELECT DISTINCT p.name 
        FROM products p 
        JOIN tags t ON p.id = t.product_id 
        WHERE t.tag IN ({placeholders})
    '''
    cursor.execute(query, search_tags)
    products = cursor.fetchall()
    conn.close()

    # Generate HTML response
    html_content = "<html><body><h1>Recommended Products</h1>"
    if not products:
        html_content += "<p>No products found matching those tags.</p>"
    else:
        html_content += "<ul>"
        for product in products:
            html_content += f"<li>{product[0]}</li>"
        html_content += "</ul>"
    html_content += "</body></html>"

    return web.Response(text=html_content, content_type='text/html')

async def handle_recommender_post(request):
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return web.Response(text="Invalid JSON", status=400)

    product_name = data.get('product_name')
    tags = data.get('tags')

    if not product_name or not isinstance(tags, list):
        return web.Response(text="Invalid input: product_name (string) and tags (array) are required", status=400)

    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Insert product
        cursor.execute('INSERT INTO products (name) VALUES (?)', (product_name,))
        product_id = cursor.lastrowid
        
        # Insert tags
        for tag in tags:
            if isinstance(tag, str):
                cursor.execute('INSERT INTO tags (product_id, tag) VALUES (?, ?)', (product_id, tag))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        return web.Response(text=str(e), status=500)
    finally:
        conn.close()

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
    app = None # Placeholder for global scope if needed
    # We use a wrapper to ensure the app is initialized properly
    async def start_server():
        global app
        app = await init_app()
        web.run_app(app, host='0.0.0.0', port=5000)

    # Since run_app is blocking, we call it directly in the main block
    # but we need to handle the async initialization of the app
    import asyncio
    
    # aiohttp.web.run_app doesn't take an async factory directly in older versions, 
    # but we can just create the app synchronously if we don't have async setup logic.
    # Let's redefine init_app as synchronous for simplicity since it doesn't actually await anything.
    
    def init_app_sync():
        app = web.Application()
        app.add_routes([
            web.get('/recommender', handle_recommender_get),
            web.post('/recommender', handle_recommender_post),
        ])
        return app

    app_sync = init_app_sync()
    web.run_app(app_sync, host='0.0.0.0', port=5000)