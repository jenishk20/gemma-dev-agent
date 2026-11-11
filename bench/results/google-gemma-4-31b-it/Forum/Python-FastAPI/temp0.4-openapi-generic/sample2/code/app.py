import os
import sqlite3
from typing import Optional, List
from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

# Configuration
DB_PATH = "db.sqlite3"
APP_SECRET = os.getenv("APP_SECRET", "default_secret_for_dev")

app = FastAPI(title="MyForum")
templates = Jinja2Templates(dirname=".") # We will use a string template for simplicity since we can't create files

# Pydantic Model for API
class Message(BaseModel):
    content: str
    username: str

# Database initialization
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

# HTML Template as a string to avoid external file dependencies
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>MyForum</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f4f4f9; }
        .message { background: white; padding: 15px; margin-bottom: 10px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .username { font-weight: bold; color: #333; }
        .content { margin-top: 5px; color: #666; white-space: pre-wrap; }
        .form-box { background: #ddd; padding: 20px; border-radius: 5px; margin-bottom: 30px; }
        input, textarea { width: 100%; padding: 8px; margin: 5px 0; box-sizing: border-box; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; border-radius: 3px; }
        .pagination { margin-top: 20px; }
        .pagination a { margin-right: 10px; text-decoration: none; color: #007bff; }
    </style>
</head>
<body>
    <h1>MyForum</h1>
    
    <div class="form-box">
        <h3>Post a Message</h3>
        <form action="/messages" method="post">
            <input type="text" name="username" placeholder="Username" required>
            <textarea name="content" placeholder="Message content..." required></textarea>
            <button type="submit">Post</button>
        </form>
    </div>

    <div class="messages">
        {% for msg in messages %}
        <div class="message">
            <div class="username">{{ msg.username }}</div>
            <div class="content">{{ msg.content }}</div>
        </div>
        {% endfor %}
    </div>

    <div class="pagination">
        {% if offset > 0 %}
            <a href="/messages?limit={{ limit }}&offset={{ offset - limit }}&sort={{ sort }}">Previous</a>
        {% endif %}
        <a href="/messages?limit={{ limit }}&offset={{ offset + limit }}&sort={{ sort }}">Next</a>
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
    
    order_by = "timestamp"
    direction = "DESC" if sort.upper() == "DESC" else "ASC"
    
    with get_db() as conn:
        cursor = conn.cursor()
        query = f"SELECT username, content FROM messages ORDER BY {order_by} {direction} LIMIT ? OFFSET ?"
        cursor.execute(query, (limit, offset))
        rows = cursor.fetchall()
        messages = [dict(row) for row in rows]

    # Using Jinja2 manually since we are restricted to one file and no external template files
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
    # The OpenAPI schema specifies application/json, but for a webapp forum, 
    # we often receive form data. We handle both to be robust.
    
    content_type = request.headers.get("Content-Type", "")
    
    if "application/json" in content_type:
        try:
            body = await request.json()
            msg = Message(**body)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON input")
    else:
        try:
            form_data = await request.form()
            username = form_data.get("username")
            content = form_data.get("content")
            if not username or not content:
                raise ValueError("Missing fields")
            msg = Message(username=username, content=content)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid form input")

    # Basic sanitization/validation
    if not msg.username.strip() or not msg.content.strip():
        raise HTTPException(status_code=400, detail="Username and content cannot be empty")

    with get_db() as conn:
        conn.execute("INSERT INTO messages (username, content) VALUES (?, ?)", (msg.username, msg.content))
        conn.commit()

    # If it was a form post, redirect back to the list
    if "application/json" not in content_type:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/messages", status_code=303)
        
    return {"status": "Successful operation"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)