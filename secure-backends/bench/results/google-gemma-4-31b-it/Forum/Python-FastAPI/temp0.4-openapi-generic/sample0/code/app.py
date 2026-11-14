import os
import sqlite3
from typing import Optional
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

# Configuration
DB_PATH = "db.sqlite3"
PORT = 5000
HOST = "0.0.0.0"

app = FastAPI(title="MyForum")
templates = Jinja2Templates(directory=".") # We will use a string template for simplicity in a single file

# Database Setup
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

init_db()

# Pydantic Model
class Message(BaseModel):
    content: str
    username: str

# HTML Template (Embedded as a string to keep everything in one file)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>MyForum</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f4f4f9; }
        .message-card { background: white; padding: 15px; margin-bottom: 10px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .username { font-weight: bold; color: #333; }
        .content { margin-top: 5px; white-space: pre-wrap; }
        .form-container { background: white; padding: 20px; border-radius: 8px; margin-bottom: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        input, textarea { width: 100%; padding: 8px; margin: 10px 0; box-sizing: border-box; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
        .pagination { margin-top: 20px; }
        .pagination a { margin-right: 10px; text-decoration: none; color: #007bff; }
    </style>
</head>
<body>
    <h1>MyForum</h1>
    
    <div class="form-container">
        <h3>Post a Message</h3>
        <form action="/messages" method="post">
            <input type="text" name="username" placeholder="Your Username" required>
            <textarea name="content" placeholder="Your Message" required></textarea>
            <button type="submit">Post</button>
        </form>
    </div>

    <h2>Messages</h2>
    {% for msg in messages %}
    <div class="message-card">
        <span class="username">{{ msg.username }}</span>
        <div class="content">{{ msg.content }}</div>
    </div>
    {% endfor %}

    <div class="pagination">
        {% if offset > 0 %}
            <a href="/messages?limit={{ limit }}&offset={{ offset - limit }}&sort={{ sort }}">« Previous</a>
        {% endif %}
        <a href="/messages?limit={{ limit }}&offset={{ offset + limit }}&sort={{ sort }}">Next »</a>
    </div>
</body>
</html>
"""

@app.get("/messages", response_class=HTMLResponse)
async def get_messages(
    request: Request, 
    limit: int = 10, 
    offset: int = 0, 
    sort: str = "DESC"
):
    # Validate sort enum
    if sort.upper() not in ["ASC", "DESC"]:
        sort = "DESC"
    
    # Use parameterized query to prevent SQL injection
    query = f"SELECT username, content FROM messages ORDER BY id {sort.upper()} LIMIT ? OFFSET ?"
    
    with get_db() as conn:
        cursor = conn.execute(query, (limit, offset))
        messages = [dict(row) for row in cursor.fetchall()]

    # We use Jinja2's Template manually since we can't create a separate .html file
    from jinja2 import Template
    template = Template(HTML_TEMPLATE)
    return template.render(
        messages=messages, 
        limit=limit, 
        offset=offset, 
        sort=sort.upper()
    )

@app.post("/messages")
async def post_message(request: Request):
    # The OpenAPI schema specifies application/json, but for a webapp forum 
    # users typically submit via HTML forms (multipart/form-data).
    # We handle both to satisfy the schema and the functional webapp requirement.
    
    content_type = request.headers.get('content-type', '')
    
    if 'application/json' in content_type:
        try:
            data = await request.json()
            msg = Message(**data)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON input")
    else:
        # Handle HTML Form submission
        form_data = await request.form()
        username = form_data.get("username")
        content = form_data.get("content")
        if not username or not content:
            raise HTTPException(status_code=400, detail="Missing username or content")
        msg = Message(username=username, content=content)

    with get_db() as conn:
        conn.execute("INSERT INTO messages (username, content) VALUES (?, ?)", (msg.username, msg.content))
        conn.commit()

    # Redirect back to the messages page
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/messages", status_code=303)

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)