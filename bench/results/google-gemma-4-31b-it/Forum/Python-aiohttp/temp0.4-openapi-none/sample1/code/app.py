import os
import sqlite3
import aiohttp.web
from aiohttp import web
from datetime import datetime

# Database setup
DB_NAME = "db.sqlite3"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_messages(limit=10, offset=0, sort='DESC'):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Validate sort to prevent SQL injection (though it's an enum in OpenAPI)
    order = "DESC" if sort.upper() == "DESC" else "ASC"
    query = f"SELECT username, content, timestamp FROM messages ORDER BY timestamp {order} LIMIT ? OFFSET ?"
    cursor.execute(query, (limit, offset))
    rows = cursor.fetchall()
    conn.close()
    return rows

def add_message(username, content):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (username, content) VALUES (?, ?)", (username, content))
    conn.commit()
    conn.close()

# HTML Template for the forum
def render_forum(messages):
    html_messages = ""
    for username, content, timestamp in messages:
        html_messages += f'<div style="border: 1px solid #ccc; margin: 10px; padding: 10px;"><strong>{username}</strong> <small>({timestamp})</small><p>{content}</p></div>'
    
    return f"""
    <html>
        <head><title>MyForum</title></head>
        <body>
            <h1>MyForum</h1>
            <form action="/messages" method="POST">
                <input type="text" name="username" placeholder="Username" required><br>
                <textarea name="content" placeholder="Message" required></textarea><br>
                <button type="submit">Post Message</button>
            </form>
            <hr>
            <div>{html_messages}</div>
            <p><a href="/messages?sort=ASC">Sort Oldest First</a> | <a href="/messages?sort=DESC">Sort Newest First</a></p>
        </body>
    </html>
    """

# Handlers
async def handle_messages(request):
    if request.method == 'GET':
        # Parse query parameters
        try:
            limit = int(request.query.get('limit', 10))
            offset = int(request.query.get('offset', 0))
            sort = request.query.get('sort', 'DESC').upper()
        except ValueError:
            limit, offset, sort = 10, 0, 'DESC'

        messages = get_messages(limit, offset, sort)
        html_content = render_forum(messages)
        return web.Response(text=html_content, content_type='text/html')

    elif request.method == 'POST':
        try:
            # The OpenAPI spec says requestBody is application/json
            # However, for a forum webapp, we check both JSON and Form data for usability
            if request.content_type == 'application/json':
                data = await request.json()
            else:
                data = await request.post()
            
            username = data.get('username')
            content = data.get('content')
            
            if not username or not content:
                return web.Response(status=400, text="Invalid input: username and content required")
            
            add_message(username, content)
            return web.Response(status=200, text="Successful operation")
        except Exception as e:
            return web.Response(status=400, text=str(e))

# App initialization
app = web.Application()
app.add_routes([web.route('GET', '/messages', handle_messages),
                web.route('POST', '/messages', handle_messages)])

if __name__ == '__main__':
    init_db()
    web.run_app(app, host='0.0.0.0', port=5000)