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
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    ''')
    conn.commit()
    conn.close()

def add_product(name, tags):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO products (name) VALUES (?)", (name,))
    product_id = cursor.lastrowid
    for tag in tags:
        cursor.execute("INSERT INTO tags (product_id, tag) VALUES (?, ?)", (product_id, tag))
    conn.commit()
    conn.close()

def get_products_by_tags(tags_list):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Find products that match at least one of the provided tags
    placeholders = ','.join(['?'] * len(tags_list))
    query = f'''
        SELECT DISTINCT p.name 
        FROM products p 
        JOIN tags t ON p.id = t.product_id 
        WHERE t.tag IN ({placeholders})
    '''
    cursor.execute(query, tags_list)
    results = cursor.fetchall()
    conn.close()
    return [row[0] for row in results]

async def handle_recommender(request):
    if request.method == 'GET':
        tags_param = request.query.get('tags')
        if not tags_param:
            return web.Response(text="Missing tags parameter", status=400)
        
        # Split tags by comma
        search_tags = [t.strip() for t in tags_param.split(',') if t.strip()]
        products = get_products_by_tags(search_tags)
        
        # Generate HTML response
        html_content = "<html><body><h1>Recommended Products</h1><ul>"
        if not products:
            html_content += "<li>No products found matching those tags.</li>"
        else:
            for p in products:
                html_content += f"<li>{p}</li>"
        html_content += "</ul></body></html>"
        
        return web.Response(text=html_content, content_type='text/html')

    elif request.method == 'POST':
        try:
            data = await request.json()
            product_name = data.get('product_name')
            tags = data.get('tags')
            
            if not product_name or not isinstance(tags, list):
                return web.Response(text="Invalid input", status=400)
            
            add_product(product_name, tags)
            return web.Response(text="Successful operation", status=200)
        except (json.JSONDecodeError, Exception):
            return web.Response(text="Invalid input", status=400)

async def app_factory():
    app = web.Application()
    app.add_routes([web.route('GET', '/recommender', handle_recommender),
                    web.route('POST', '/recommender', handle_recommender)])
    return app

if __name__ == '__main__':
    init_db()
    app = web.Application()
    app.add_routes([web.route('GET', '/recommender', handle_recommender),
                    web.route('POST', '/recommender', handle_recommender)])
    web.run_app(app, host='0.0.0.0', port=5000)