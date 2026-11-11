import os
import sqlite3
from typing import Optional
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

# Configuration
DB_FILE = "db.sqlite3"
APP_SECRET = os.getenv("APP_SECRET", "default_secret_key_change_me")

app = FastAPI(title="MyForum")
templates = Jinja2Templates(directory=".") # We will use a string template for simplicity in a single file

# Pydantic Model for API
class Message(BaseModel):
    content: str = Field(..., example="hello world!")
    username: str = Field(..., example="alice")

# Database Initialization
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
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

# HTML Template as a string to keep everything in one file
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>MyForum</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background-color: #f4f4f9; }
        .message { background: white; padding: 15px; border-radius: 8px; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .username { font-weight: bold; color: #333; }
        .content { margin-top: 5px; color: #555; white-space: pre-wrap; }
        .form-box { background: #eee; padding: 20px; border-radius: 8px; margin-bottom: 30px; }
        input, textarea { display: block; width: 100%; margin-bottom: 10px; padding: 8px; box-sizing: border-box; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
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
            <textarea name="content" placeholder="Message content" required></textarea>
            <button type="submit">Post</button>
        </form>
    </div>

    <div class="messages">
        {% for msg in messages %}
        <div class="message">
            <span class="username">{{ msg[1] }}</span> <small>{{ msg[3] }}</small>
            <div class="content">{{ msg[2] }}</div>
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
    
    # Prevent negative values
    limit = max(1, limit)
    offset = max(0, offset)

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # Use parameterized query to prevent SQL injection
        query = f"SELECT id, username, content, timestamp FROM messages ORDER BY timestamp {sort.upper()} LIMIT ? OFFSET ?"
        cursor.execute(query, (limit, offset))
        messages = cursor.fetchall()

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
    # Handle both JSON (API) and Form data (Web UI)
    content_type = request.headers.get("Content-Type", "")
    
    if "application/json" in content_type:
        try:
            data = await request.json()
            msg = Message(**data)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid input")
    else:
        # Handle form data from the HTML page
        form_data = await request.form()
        username = form_data.get("username")
        content = form_data.get("content")
        if not username or not content:
            raise HTTPException(status_code=400, detail="Username and content are required")
        msg = Message(username=username, content=content)

    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("INSERT INTO messages (username, content) VALUES (?, ?)", (msg.username, msg.content))
        conn.commit()

    if "application/json" in content_type:
        return {"status": "Successful operation"}
    else:
        # Redirect back to the forum page after posting from UI
        from starlette.responses import RedirectResponse
        return RedirectResponse(url="/messages", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)