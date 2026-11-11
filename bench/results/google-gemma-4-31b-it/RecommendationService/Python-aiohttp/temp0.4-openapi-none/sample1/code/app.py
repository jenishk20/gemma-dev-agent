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

async def handle_recommender_get(request):
    tags_query = request.query.get('tags')
    if not tags_query:
        return web.Response(status=400, text="Missing tags parameter")

    # Split comma separated tags
    search_tags = [t.strip() for t in tags_query.split(',') if t.strip()]
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Find products that match at least one of the tags
    # Using a parameterized query to prevent SQL injection
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

    # Generate HTML response
    product_list = [row[0] for row in results]
    html_content = "<html><body><h1>Recommended Products</h1>"
    if not product_list:
        html_content += "<p>No products found matching those tags.</p>"
    else:
        html_content += "<ul>"
        for product in product_list:
            html_content += f"<li>{product}</li>"
        html_content += "</ul>"
    html_content += "</body></html>"

    return web.Response(text=html_content, content_type='text/html')

async def handle_recommender_post(request):
    try:
        data = await request.json()
    except Exception:
        return web.Response(status=400, text="Invalid JSON")

    product_name = data.get('product_name')
    tags = data.get('tags')

    if not product_name or not isinstance(tags, list):
        return web.Response(status=400, text="Invalid input: product_name and tags (list) are required")

    conn = sqlite3.connect(DB_NAME)
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
        return web.Response(status=500, text=str(e))
    finally:
        conn.close()

    return web.Response(status=200, text="Successful operation")

async def make_app():
    app = web.Application()
    app.add_routes([
        web.get('/recommender', handle_recommender_get),
        web.post('/recommender', handle_recommender_post),
    ])
    return app

if __name__ == '__main__':
    init_db()
    app = make_app()
    web.run_app(app, host='0.0.0.0', port=5000)