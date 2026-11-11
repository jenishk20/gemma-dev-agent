import sqlite3
import os
from typing import Optional, List
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import uvicorn
from jinja2 import Template, escape

# Configuration
DB_FILE = "db.sqlite3"
APP_SECRET = os.getenv("APP_SECRET", "default_secret")

app = FastAPI(title="MyForum")

# Pydantic Model with basic validation to prevent resource exhaustion (max lengths)
class Message(BaseModel):
    content: str = Field(..., max_length=10000)
    username: str = Field(..., max_length=255)

# Database initialization
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

# HTML Template as a string. 
# Note: Jinja2 auto-escapes variables by default when using the Template object 
# if configured, but we will explicitly handle it or use the standard render.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>MyForum</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background-color: #f4f4f9; }
        .message { background: white; padding: 15px; margin-bottom: 10px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .username { font-weight: bold; color: #333; }
        .content { margin-top: 5px; white-space: pre-wrap; }
        .form-box { background: white; padding: 20px; border-radius: 5px; margin-bottom: 30px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        input, textarea { width: 100%; padding: 10px; margin: 10px 0; box-sizing: border-box; }
        button { background: #007bff; color: white; border: none; padding: 10px 20px; cursor: pointer; border-radius: 3px; }
        .pagination { margin-top: 20px; }
    </style>
</head>
<body>
    <h1>MyForum</h1>
    <div class="form-box">
        <h3>Post a Message</h3>
        <form action="/messages" method="post" id="msgForm">
            <input type="text" name="username" placeholder="Username" required>
            <textarea name="content" placeholder="Message content" required></textarea>
            <button type="submit">Post</button>
        </form>
        <script>
            document.getElementById('msgForm').onsubmit = async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                const data = {
                    username: formData.get('username'),
                    content: formData.get('content')
                };
                try {
                    const res = await fetch('/messages', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(data)
                    });
                    if (res.ok) { window.location.reload(); } else { alert('Error posting message'); }
                } catch (err) { alert('Network error'); }
            };
        </script>
    </div>
    <div class="messages">
        {% for msg in messages %}
        <div class="message">
            <span class="username">{{ msg[1] }}</span>
            <div class="content">{{ msg[2] }}</div>
            <small style="color: #888;">{{ msg[3] }}</small>
        </div>
        {% endfor %}
    </div>
    <div class="pagination">
        <a href="/messages?offset={{ offset }}&limit={{ limit }}&sort={{ sort }}">Refresh</a>
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
    # 1. Validate and sanitize input for the ORDER BY clause (which cannot be parameterized)
    # Only allow explicit values from the enum defined in OpenAPI
    sort_upper = sort.upper()
    if sort_upper not in ["ASC", "DESC"]:
        sort_upper = "DESC"
    
    # 2. Prevent resource exhaustion by capping limit
    safe_limit = min(max(0, limit), 100)
    safe_offset = max(0, offset)

    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            # Use parameterized queries for limit and offset to prevent SQL injection
            # sort_upper is safe because it is strictly validated against a whitelist
            query = f"SELECT id, username, content, timestamp FROM messages ORDER BY timestamp {sort_upper} LIMIT ? OFFSET ?"
            cursor.execute(query, (safe_limit, safe_offset))
            messages = cursor.fetchall()
    except Exception:
        # Generic error to avoid leaking internal DB details
        raise HTTPException(status_code=500, detail="Internal Server Error")

    # 3. Prevent XSS: Jinja2 templates auto-escape variables by default.
    # We use the Template object which handles the escaping of the provided data.
    template = Template(HTML_TEMPLATE)
    return template.render(
        messages=messages, 
        limit=safe_limit, 
        offset=safe_offset, 
        sort=sort_upper
    )

@app.post("/messages")
async def post_message(msg: Message):
    try:
        # Use parameterized queries to prevent SQL injection
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("INSERT INTO messages (username, content) VALUES (?, ?)", (msg.username, msg.content))
            conn.commit()
        return {"status": "Successful operation"}
    except Exception:
        # Return 400 as per OpenAPI spec for invalid input or processing errors
        raise HTTPException(status_code=400, detail="Invalid input")

if __name__ == "__main__":
    # Run on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)