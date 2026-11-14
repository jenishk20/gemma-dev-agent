import sqlite3
import os
from typing import Optional
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

# Database initialization
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

init_db()

app = FastAPI(title="MyForum")
templates = Jinja2Templates(request=None) # We will pass request in context

# Pydantic model for JSON POST requests as per OpenAPI schema
class Message(BaseModel):
    content: str
    username: str

# HTML Template embedded as a string to keep everything in one file
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>MyForum</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f4f4f9; }
        .message { background: white; padding: 15px; margin-bottom: 10px; border-radius: 5px; border: 1px solid #ddd; }
        .username { font-weight: bold; color: #333; }
        .content { margin-top: 5px; white-space: pre-wrap; }
        .form-box { background: #eee; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        input, textarea { display: block; width: 100%; margin-bottom: 10px; padding: 8px; box-sizing: border-box; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; }
        .pagination { margin-top: 20px; }
    </style>
</head>
<body>
    <h1>MyForum</h1>
    
    <div class="form-box">
        <h3>Post a Message</h3>
        <form method="POST" action="/messages">
            <input type="text" name="username" placeholder="Username" required>
            <textarea name="content" placeholder="Message content" required></textarea>
            <button type="submit">Post</button>
        </form>
    </div>

    <h2>Messages</h2>
    <div>
        {% for msg in messages %}
        <div class="message">
            <span class="username">{{ msg[1] }}</span> <small>at {{ msg[3] }}</small>
            <div class="content">{{ msg[2] }}</div>
        </div>
        {% endfor %}
    </div>

    <div class="pagination">
        <a href="/messages?limit=10&offset={{ offset - 10 if offset > 0 else 0 }}&sort={{ sort }}">Previous</a> | 
        <a href="/messages?limit=10&offset={{ offset + 10 }}&sort={{ sort }}">Next</a>
    </div>
</body>
</html>
"""

# Manual template setup since we can't use external files
from jinja2 import Template
jinja_template = Template(HTML_TEMPLATE)

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
    
    order_clause = "DESC" if sort.upper() == "DESC" else "ASC"
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # Use parameterized query to prevent SQL injection
            query = f"SELECT id, username, content, timestamp FROM messages ORDER BY timestamp {order_clause} LIMIT ? OFFSET ?"
            cursor.execute(query, (limit, offset))
            messages = cursor.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return jinja_template.render(
        messages=messages, 
        offset=offset, 
        sort=sort.upper()
    )

@app.post("/messages")
async def post_message(request: Request):
    # The OpenAPI schema specifies application/json, but for a webapp we often use form-data.
    # To support both as a robust webapp:
    
    content_type = request.headers.get('content-type', '')
    
    if 'application/json' in content_type:
        try:
            data = await request.json()
            msg = Message(**data)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON input")
    else:
        # Fallback to form data for the HTML UI
        try:
            form_data = await request.form()
            username = form_data.get("username")
            content = form_data.get("content")
            if not username or not content:
                raise HTTPException(status_code=400, detail="Missing username or content")
            msg = Message(username=username, content=content)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid form input")

    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT INTO messages (username, content) VALUES (?, ?)", (msg.username, msg.content))
            conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # If it was a JSON request, return 200. If it was a form, redirect to the forum page.
    if 'application/json' in content_type:
        return {"status": "Successful operation"}
    else:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/messages", status_code=303)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)