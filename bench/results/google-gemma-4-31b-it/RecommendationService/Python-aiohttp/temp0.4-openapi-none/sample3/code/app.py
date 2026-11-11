import os
import sqlite3
import json
from aiohttp import web

# Database helper to handle synchronous sqlite3 calls
def init_db():
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            product_id INTEGER,
            tag TEXT,
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    ''')
    conn.commit()
    conn.close()

def add_product(name, tags):
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO products (name) VALUES (?)', (name,))
    product_id = cursor.lastrowid
    for tag in tags:
        cursor.execute('INSERT INTO tags (product_id, tag) VALUES (?, ?)', (product_id, tag))
    conn.commit()
    conn.close()

def get_products_by_tags(search_tags):
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    # Find products that have at least one of the provided tags
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
    return [row[0] for row in results]

async def handle_recommender_get(request):
    tags_param = request.query.get('tags')
    if not tags_param:
        return web.Response(status=400, text="Missing tags parameter")
    
    search_tags = [t.strip() for t in tags_param.split(',') if t.strip()]
    products = get_products_by_tags(search_tags)
    
    # Generate HTML response as per schema
    html_content = "<html><body><h1>Recommended Products</h1><ul>"
    if not products:
        html_content += "<li>No products found matching these tags.</li>"
    for product in products:
        html_content += f"<li>{product}</li>"
    html_content += "</ul></body></html>"
    
    return web.Response(text=html_content, content_type='text/html')

async def handle_recommender_post(request):
    try:
        data = await request.json()
        product_name = data.get('product_name')
        tags = data.get('tags')
        
        if not product_name or not isinstance(tags, list):
            return web.Response(status=400, text="Invalid input")
        
        add_product(product_name, tags)
        return web.Response(status=200, text="Successful operation")
    except json.JSONDecodeError:
        return web.Response(status=400, text="Invalid JSON")

def main():
    init_db()
    app = web.Application()
    app.add_routes([
        web.get('/recommender', handle_recommender_get),
        web.post('/recommender', handle_recommender_post),
    ])
    web.run_app(app, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    main()