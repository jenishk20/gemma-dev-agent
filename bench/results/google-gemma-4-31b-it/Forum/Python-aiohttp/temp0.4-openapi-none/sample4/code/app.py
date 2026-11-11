import os
import sqlite3
import asyncio
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

def get_db_connection():
    return sqlite3.connect(DB_NAME)

# HTML Template for the forum
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>MyForum</title>
    <style>
        body {{ font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f4f4f9; }}
        .message {{ background: white; padding: 15px; margin-bottom: 10px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .username {{ font-weight: bold; color: #333; }}
        .content {{ margin-top: 5px; }}
        .form-container {{ background: #fff; padding: 20px; border-radius: 5px; margin-bottom: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        input, textarea {{ display: block; width: 100%; margin-bottom: 10px; padding: 8px; box-sizing: border-box; }}
        button {{ padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; border-radius: 3px; }}
        .pagination {{ margin-top: 20px; }}
    </style>
</head>
<body>
    <h1>MyForum</h1>
    
    <div class="form-container">
        <h3>Post a Message</h3>
        <form action="/messages" method="POST">
            <input type="text" name="username" placeholder="Username" required>
            <textarea name="content" placeholder="Message content" required></textarea>
            <button type="submit">Post</button>
        </form>
    </div>

    <div class="messages">
        <h3>Messages</h3>
        {messages_html}
    </div>

    <div class="pagination">
        <a href="/messages?sort=ASC">Oldest First</a> | 
        <a href="/messages?sort=DESC">Newest First</a>
    </div>
</body>
</html>
"""

async def handle_messages(request):
    # Handle POST (Create Message)
    if request.method == 'POST':
        try:
            # The schema specifies application/json, but for a webapp we handle both
            # to allow the HTML form to work.
            if request.content_type == 'application/json':
                data = await request.json()
            else:
                data = await request.post()
                data = {k: v for k, v in data.items()}

            username = data.get('username')
            content = data.get('content')

            if not username or not content:
                return web.Response(status=400, text="Invalid input")

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO messages (username, content) VALUES (?, ?)', (username, content))
            conn.commit()
            conn.close()
            
            # Redirect back to the main page
            return web.Response(status=303, headers={'Location': '/messages'})
        except Exception:
            return web.Response(status=400, text="Invalid input")

    # Handle GET (List Messages)
    elif request.method == 'GET':
        limit = int(request.query.get('limit', 10))
        offset = int(request.query.get('offset', 0))
        sort = request.query.get('sort', 'DESC').upper()
        
        if sort not in ['ASC', 'DESC']:
            sort = 'DESC'

        conn = get_db_connection()
        cursor = conn.cursor()
        
        order_clause = f"ORDER BY timestamp {sort}"
        cursor.execute(f'SELECT username, content, timestamp FROM messages {order_clause} LIMIT ? OFFSET ?', (limit, offset))
        rows = cursor.fetchall()
        conn.close()

        messages_html = ""
        for row in rows:
            messages_html += f'<div class="message"><span class="username">{row[0]}</span> <small>{row[2]}</small><div class="content">{row[1]}</div></div>'
        
        if not rows:
            messages_html = "<p>No messages yet.</p>"

        return web.Response(text=HTML_TEMPLATE.format(messages_html=messages_html), content_type='text/html')

async def app_factory():
    app = web.Application()
    app.add_routes([web.get('/messages', handle_messages), 
                    web.post('/messages', handle_messages)])
    # Root redirect
    app.router.add_get('/', lambda r: web.Response(status=303, headers={'Location': '/messages'}))
    return app

if __name__ == "__main__":
    init_db()
    web.run_app(app_factory(), port=5000, address='0.0.0.0')