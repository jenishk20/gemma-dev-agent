import os
import sqlite3
from typing import Optional
from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

# Configuration
DB_PATH = "db.sqlite3"
APP_SECRET = os.getenv("APP_SECRET", "default_secret_key")

app = FastAPI(title="MyForum")
templates = Jinja2Templates(request=Request)

# Pydantic Model for API
class Message(BaseModel):
    content: str
    username: str

# Database initialization
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
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

# Helper to get DB connection
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# HTML Template as a string to keep everything in one file
# Since Jinja2Templates usually looks for files, we will override the response 
# by using a custom template string or a simple HTML generator.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>MyForum</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f4f4f9; }
        .message { background: white; padding: 15px; margin-bottom: 10px; border-radius: 5px; border: 1px solid #ddd; }
        .username { font-weight: bold; color: #333; }
        .content { margin-top: 5px; }
        .form-box { background: white; padding: 20px; border-radius: 5px; border: 1px solid #ddd; margin-bottom: 30px; }
        input, textarea { width: 100%; padding: 8px; margin: 10px 0; box-sizing: border-box; }
        button { background: #007bff; color: white; border: none; padding: 10px 20px; cursor: pointer; border-radius: 3px; }
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
    <h2>Messages</h2>
    {% for msg in messages %}
        <div class="message">
            <div class="username">{{ msg.username }}</div>
            <div class="content">{{ msg.content }}</div>
        </div>
    {% endfor %}
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
    
    order_clause = "timestamp ASC" if sort.upper() == "ASC" else "timestamp DESC"
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute(f"SELECT username, content FROM messages ORDER BY {order_clause} LIMIT ? OFFSET ?", (limit, offset))
    rows = cursor.fetchall()
    db.close()
    
    messages = [dict(row) for row in rows]
    
    # Use Jinja2 to render the string template
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
    # The OpenAPI schema specifies application/json for the POST request
    # However, for a webapp forum, we should handle both JSON and Form data
    # to allow the HTML form to work.
    
    content_type = request.headers.get("Content-Type", "")
    
    if "application/json" in content_type:
        try:
            data = await request.json()
            msg = Message(**data)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON input")
    else:
        # Handle HTML Form submission
        try:
            form_data = await request.form()
            msg = Message(
                username=form_data.get("username", ""),
                content=form_data.get("content", "")
            )
            if not msg.username or not msg.content:
                raise ValueError("Missing fields")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid form input")

    # Sanitize input is handled by the DB driver (parameterized queries)
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO messages (username, content) VALUES (?, ?)", (msg.username, msg.content))
    db.commit()
    db.close()
    
    # If it was a form request, redirect back to the forum page
    if "application/json" not in content_type:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/messages", status_code=303)
        
    return {"status": "Successful operation"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)