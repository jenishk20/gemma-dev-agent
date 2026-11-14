import os
import sqlite3
import json
from aiohttp import web

# Database initialization
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
    # Validate sort to prevent SQL injection
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
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>MyForum</title>
    <style>
        body {{ font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .message {{ border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; border-radius: 5px; }}
        .username {{ font-weight: bold; color: #333; }}
        .timestamp {{ font-size: 0.8em; color: #666; }}
        .form-box {{ background: #f9f9f9; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <h1>MyForum</h1>
    <div class="form-box">
        <h3>Post a Message</h3>
        <form action="/messages" method="POST">
            <input type="text" name="username" placeholder="Username" required><br><br>
            <textarea name="content" placeholder="Message content" required></textarea><br><br>
            <button type="submit">Post</button>
        </form>
    </div>
    <hr>
    <div class="messages">
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
        except ValueError:
            return web.Response(text="Invalid parameters", status=400)

        messages = get_messages(limit, offset, sort)
        
        msg_html = ""
        for user, content, ts in messages:
            msg_html += f'<div class="message"><span class="username">{user}</span> <span class="timestamp">({ts})</span><p>{content}</p></div>'
        
        full_html = HTML_TEMPLATE.format(messages_html=msg_html if msg_html else "<p>No messages yet!</p>")
        return web.Response(text=full_html, content_type='text/html')

    elif request.method == 'POST':
        try:
            # The OpenAPI spec says application/json
            data = await request.json()
            username = data.get('username')
            content = data.get('content')
            
            if not username or not content:
                return web.Response(status=400, text="Missing username or content")
            
            add_message(username, content)
            return web.Response(status=200, text="Message posted successfully")
        except Exception as e:
            # If it's not JSON, it might be a form submission from the HTML page
            # To support the HTML form provided in the template, we handle form data too
            try:
                data = await request.post()
                username = data.get('username')
                content = data.get('content')
                if username and content:
                    add_message(username, content)
                    return web.Response(text="Message posted! <a href='/messages'>Go back</a>", content_type='text/html')
            except:
                pass
            return web.Response(status=400, text="Invalid input")

app = web.Application()
app.add_routes([web.route('/messages', handle_messages, methods=['GET', 'POST'])])

if __name__ == '__main__':
    init_db()
    web.run_app(app, host='0.0.0.0', port=5000)