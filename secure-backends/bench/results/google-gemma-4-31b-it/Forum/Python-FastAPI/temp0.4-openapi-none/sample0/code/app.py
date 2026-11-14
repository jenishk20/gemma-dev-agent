import sqlite3
import os
from typing import Optional, List
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

# Database setup
DB_PATH = "db.sqlite3"

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

# Pydantic Model
class Message(BaseModel):
    content: str
    username: str

# FastAPI App
app = FastAPI(title="MyForum")
templates = Jinja2Templates(request_locale=None)

# Since we must put everything in one file and Jinja2Templates usually 
# expects a directory, we will use a custom template string approach 
# or a minimal directory setup. To ensure it works in one file, 
# we'll define the HTML directly in the response.

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>MyForum</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f4f4f9; }
        .message { background: white; padding: 10px; margin-bottom: 10px; border-radius: 5px; border: 1px solid #ddd; }
        .username { font-weight: bold; color: #555; }
        .content { margin-top: 5px; }
        .form-box { background: #eee; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        input, textarea { display: block; margin-bottom: 10px; width: 100%; padding: 8px; box-sizing: border-box; }
        button { padding: 10px 20px; cursor: pointer; background: #007bff; color: white; border: none; border-radius: 3px; }
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
    <hr>
    <h2>Messages</h2>
    {% for msg in messages %}
        <div class="message">
            <span class="username">{{ msg[1] }}</span> <small>{{ msg[3] }}</small>
            <div class="content">{{ msg[2] }}</div>
        </div>
    {% endfor %}
    <div style="margin-top: 20px;">
        <a href="/messages?sort=ASC">Oldest First</a> | 
        <a href="/messages?sort=DESC">Newest First</a>
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
    if sort not in ["ASC", "DESC"]:
        sort = "DESC"
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        query = f"SELECT id, username, content, timestamp FROM messages ORDER BY timestamp {sort} LIMIT ? OFFSET ?"
        cursor.execute(query, (limit, offset))
        messages = cursor.fetchall()
    
    # Manual rendering of the template since we can't create a folder
    from jinja2 import Template
    template = Template(HTML_TEMPLATE)
    return template.render(request=request, messages=messages)

@app.post("/messages")
async def post_message(request: Request):
    # The OpenAPI schema specifies application/json for the POST request body.
    # However, for a forum webapp, HTML forms send application/x-www-form-urlencoded.
    # To support both (API and Web UI), we check the content type.
    
    content_type = request.headers.get('content-type', '')
    
    if 'application/json' in content_type:
        try:
            data = await request.json()
            msg = Message(**data)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid input")
    else:
        # Handle form submission from the HTML page
        form_data = await request.form()
        username = form_data.get("username")
        content = form_data.get("content")
        if not username or not content:
            raise HTTPException(status_code=400, detail="Invalid input")
        msg = Message(username=username, content=content)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT INTO messages (username, content) VALUES (?, ?)", (msg.username, msg.content))
        conn.commit()
    
    # If it's a form request, redirect back to the messages page
    if 'application/json' not in content_type:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/messages", status_code=303)
        
    return {"status": "Successful operation"}

if __name__ == "__main__":
    init_db()
    uvicorn.run(app, host="0.0.0.0", port=5000)