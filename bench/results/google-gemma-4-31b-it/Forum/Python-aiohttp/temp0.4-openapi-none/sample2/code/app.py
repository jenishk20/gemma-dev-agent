import os
import sqlite3
import asyncio
from aiohttp import web
from datetime import datetime

# Database setup
DB_NAME = "db.sqlite3"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

async def get_messages(limit, offset, sort):
    def sync_get():
        with sqlite3.connect(DB_NAME) as conn:
            order = "DESC" if sort.upper() == "DESC" else "ASC"
            query = f"SELECT username, content, timestamp FROM messages ORDER BY timestamp {order} LIMIT ? OFFSET ?"
            return conn.execute(query, (limit, offset)).fetchall()
    
    return await asyncio.to_thread(sync_get)

async def add_message(username, content):
    def sync_add():
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("INSERT INTO messages (username, content) VALUES (?, ?)", (username, content))
            conn.commit()
    
    await asyncio.to_thread(sync_add)

# HTML Template for the forum
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>MyForum</title>
    <style>
        body {{ font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .message {{ border-bottom: 1px solid #ccc; padding: 10px 0; }}
        .username {{ font-weight: bold; color: #333; }}
        .timestamp {{ font-size: 0.8em; color: #666; }}
        .form-box {{ background: #f4f4f4; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        input, textarea {{ display: block; margin-bottom: 10px; width: 100%; }}
    </style>
</head>
<body>
    <h1>MyForum</h1>
    <div class="form-box">
        <h3>Post a Message</h3>
        <form action="/messages" method="post">
            <input type="text" name="username" placeholder="Username" required>
            <textarea name="content" placeholder="Message content" required></textarea>
            <button type="submit">Post</button>
        </form>
    </div>
    <div id="messages">
        {messages_html}
    </div>
</body>
</html>
"""

async def handle_messages(request):
    if request.method == 'GET':
        # Parse query parameters
        try:
            limit = int(request.query.get('limit', 10))
            offset = int(request.query.get('offset', 0))
            sort = request.query.get('sort', 'DESC').upper()
            if sort not in ['ASC', 'DESC']:
                sort = 'DESC'
        except ValueError:
            limit, offset, sort = 10, 0, 'DESC'

        messages = await get_messages(limit, offset, sort)
        
        messages_html = ""
        for username, content, timestamp in messages:
            messages_html += f'<div class="message"><span class="username">{username}</span> <span class="timestamp">({timestamp})</span><p>{content}</p></div>'
        
        # If no messages, show a placeholder
        if not messages:
            messages_html = "<p>No messages yet.</p>"

        return web.Response(text=HTML_TEMPLATE.format(messages_html=messages_html), content_type='text/html')

    elif request.method == 'POST':
        try:
            # The schema says application/json, but for a webapp forum, 
            # we handle both JSON and Form data for usability.
            if request.content_type == 'application/json':
                data = await request.json()
            else:
                data = await request.post()
                # Convert MultiDict to dict for the logic below
                data = {k: v for k, v in data.items()}

            username = data.get('username')
            content = data.get('content')

            if not username or not content:
                return web.Response(status=400, text="Invalid input: username and content are required")

            await add_message(username, content)
            
            # Redirect back to the messages page
            return web.Response(status=303, headers={'Location': '/messages'})
        except Exception as e:
            return web.Response(status=400, text=str(e))

async def app_factory():
    app = web.Application()
    app.add_routes([web.get('/messages', handle_messages),
                    web.post('/messages', handle_messages)])
    return app

if __name__ == "__main__":
    init_db()
    app = web.Application()
    app.router.add_get('/messages', handle_messages)
    app.router.add_post('/messages', handle_messages)
    web.run_app(app, host='0.0.0.0', port=5000)