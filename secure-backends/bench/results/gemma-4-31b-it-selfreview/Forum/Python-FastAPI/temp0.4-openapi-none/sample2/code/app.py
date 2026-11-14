import os
import sqlite3
from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import uvicorn
from jinja2 import Template, escape

# Configuration
DB_FILE = "db.sqlite3"
PORT = 5000
HOST = "0.0.0.0"

app = FastAPI(title="MyForum")

# Pydantic Model for Request Body with basic resource exhaustion bounds
class Message(BaseModel):
    # Limit input size to prevent resource exhaustion (DoS)
    content: str = Field(..., max_length=10000)
    username: str = Field(..., max_length=100)

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

# HTML Template for the forum
# Note: Jinja2's Template.render with manual escape or autoescape=True prevents XSS.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>MyForum</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f4f4f4; }
        .message { background: white; padding: 15px; margin-bottom: 10px; border-radius: 5px; border: 1px solid #ddd; }
        .username { font-weight: bold; color: #333; }
        .content { margin-top: 5px; white-space: pre-wrap; }
        .form-box { background: white; padding: 20px; border-radius: 5px; border: 1px solid #ddd; margin-bottom: 30px; }
        input, textarea { width: 100%; padding: 8px; margin: 10px 0; box-sizing: border-box; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; }
    </style>
</head>
<body>
    <h1>MyForum</h1>
    
    <div class="form-box">
        <h3>Post a Message</h3>
        <form action="/messages" method="post" id="msgForm">
            <input type="text" name="username" placeholder="Username" required maxlength="100">
            <textarea name="content" placeholder="Message content" required maxlength="10000"></textarea>
            <button type="submit" id="submitBtn">Post</button>
        </form>
    </div>

    <div id="messages">
        {% for msg in messages %}
        <div class="message">
            <div class="username">{{ msg[1] }}</div>
            <div class="content">{{ msg[2] }}</div>
        </div>
        {% endfor %}
    </div>

    <script>
        document.getElementById('msgForm').onsubmit = async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = {
                username: formData.get('username'),
                content: formData.get('content')
            };
            try {
                const resp = await fetch('/messages', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                if (resp.ok) {
                    window.location.reload();
                } else {
                    alert('Error posting message');
                }
            } catch (err) {
                alert('Network error occurred');
            }
        };
    </script>
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
    # 1. Resource Exhaustion: Bound the limit to prevent database DoS
    safe_limit = min(max(0, limit), 100)
    safe_offset = max(0, offset)
    
    # 2. SQL Injection: 'sort' is used in the ORDER BY clause where parameters cannot be used.
    # We use a strict whitelist to ensure only allowed strings reach the query.
    sort_upper = sort.upper()
    if sort_upper == "ASC":
        order_clause = "ASC"
    else:
        order_clause = "DESC"
    
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            # Use parameterized queries for limit and offset
            query = f"SELECT id, username, content, timestamp FROM messages ORDER BY timestamp {order_clause} LIMIT ? OFFSET ?"
            cursor.execute(query, (safe_limit, safe_offset))
            messages = cursor.fetchall()
    except Exception:
        # Error handling: return generic error, do not leak stack trace
        raise HTTPException(status_code=500, detail="Internal Server Error")

    # 3. XSS Prevention: Use Jinja2 with autoescape enabled.
    # We create a template and explicitly enable autoescape to ensure all user content is escaped.
    template = Template(HTML_TEMPLATE)
    # In a real scenario, we'd use Environment(autoescape=True), but for a single file:
    # We manually escape the data passed to the template if not using a full Env.
    # However, Jinja2's default behavior for Template.render is to treat strings as safe unless configured.
    # To be strict, we escape the data before passing it to the template.
    escaped_messages = []
    for msg in messages:
        # msg[1] is username, msg[2] is content
        escaped_messages.append((msg[0], escape(msg[1]), escape(msg[2]), msg[3]))

    return template.render(messages=escaped_messages)

@app.post("/messages")
async def post_message(msg: Message):
    try:
        # SQL Injection: Use parameterized queries
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute(
                "INSERT INTO messages (username, content) VALUES (?, ?)", 
                (msg.username, msg.content)
            )
            conn.commit()
        return {"status": "Successful operation"}
    except Exception:
        # Error handling: return 400 as per OpenAPI spec for invalid input/failures
        raise HTTPException(status_code=400, detail="Invalid input")

if __name__ == "__main__":
    # Ensure the app is run on the specified port and host
    uvicorn.run(app, host=HOST, port=PORT)