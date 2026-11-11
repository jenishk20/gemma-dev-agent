import os
import sqlite3
import json
from aiohttp import web

# Database configuration
DB_FILE = "db.sqlite3"

def init_db():
    conn = sqlite3.connect(DB_FILE)
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
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

async def handle_messages(request):
    if request.method == 'GET':
        # Parse query parameters
        try:
            limit = int(request.query.get('limit', 10))
            offset = int(request.query.get('offset', 0))
            sort = request.query.get('sort', 'DESC').upper()
        except ValueError:
            return web.Response(text="Invalid query parameters", status=400)

        if sort not in ['ASC', 'DESC']:
            sort = 'DESC'

        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = f"SELECT username, content, timestamp FROM messages ORDER BY timestamp {sort} LIMIT ? OFFSET ?"
        cursor.execute(query, (limit, offset))
        rows = cursor.fetchall()
        conn.close()

        # Generate simple HTML response as per OpenAPI schema (text/html)
        html = "<html><body><h1>MyForum</h1>"
        html += '<form method="POST" action="/messages">'
        html += 'Username: <input name="username"><br>'
        html += 'Message: <input name="content"><br>'
        html += '<button type="submit">Post</button></form><hr>'
        html += '<ul>'
        for row in rows:
            html += f"<li><b>{row['username']}</b> ({row['timestamp']}): {row['content']}</li>"
        html += '</ul></body></html>'
        
        return web.Response(text=html, content_type='text/html')

    elif request.method == 'POST':
        try:
            # The schema specifies application/json for the POST requestBody
            data = await request.json()
            username = data.get('username')
            content = data.get('content')

            if not username or not content:
                return web.Response(text="Missing username or content", status=400)

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO messages (username, content) VALUES (?, ?)", (username, content))
            conn.commit()
            conn.close()
            
            return web.Response(text="Successful operation", status=200)
        except json.JSONDecodeError:
            # Fallback for HTML form submission if the user uses the browser form provided in GET
            try:
                data = await request.post()
                username = data.get('username')
                content = data.get('content')
                if not username or not content:
                    return web.Response(text="Missing username or content", status=400)
                
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO messages (username, content) VALUES (?, ?)", (username, content))
                conn.commit()
                conn.close()
                return web.Response(text="Successful operation", status=200)
            except Exception:
                return web.Response(text="Invalid input", status=400)
        except Exception as e:
            return web.Response(text=str(e), status=400)

async def app_factory():
    app = web.Application()
    app.add_routes([web.route('/messages', handle_messages, methods=['GET', 'POST'])])
    return app

if __name__ == '__main__':
    init_db()
    web.run_app(app_factory(), port=5000, address='0.0.0.0')