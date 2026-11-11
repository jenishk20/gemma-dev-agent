import os
import sqlite3
from typing import Optional, List
from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

# --- Database Setup ---
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

# --- Models ---
class Message(BaseModel):
    content: str
    username: str

# --- App Initialization ---
app = FastAPI(title="MyForum")
templates = Jinja2Templates(request=None) # We will pass request in the call

# Simple HTML template embedded as a string for single-file requirement
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>MyForum</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .message { border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; border-radius: 5px; }
        .username { font-weight: bold; color: #555; }
        .content { margin-top: 5px; }
        .form-group { margin-bottom: 15px; }
        input, textarea { width: 100%; padding: 8px; margin-top: 5px; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; }
    </style>
</head>
<body>
    <h1>MyForum</h1>
    
    <div style="background: #f9f9f9; padding: 20px; border-radius: 5px; margin-bottom: 30px;">
        <h3>Post a Message</h3>
        <form action="/messages" method="post" id="postForm">
            <div class="form-group">
                <label>Username:</label><br>
                <input type="text" name="username" required>
            </div>
            <div class="form-group">
                <label>Message:</label><br>
                <textarea name="content" required></textarea>
            </div>
            <button type="submit">Post</button>
        </form>
        <!-- Hidden input to handle JSON requirement of the OpenAPI spec via JS -->
        <script>
            document.getElementById('postForm').onsubmit = async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                const data = {
                    username: formData.get('username'),
                    content: formData.get('content')
                };
                const response = await fetch('/messages', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                if (response.ok) {
                    window.location.reload();
                } else {
                    alert('Error posting message');
                }
            };
        </script>
    </div>

    <h2>Messages</h2>
    {% for msg in messages %}
        <div class="message">
            <div class="username">{{ msg[1] }}</div>
            <div class="content">{{ msg[2] }}</div>
            <small style="color: #999;">{{ msg[3] }}</small>
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
    if sort.upper() not in ["ASC", "DESC"]:
        sort = "DESC"
    
    order_clause = "ASC" if sort.upper() == "ASC" else "DESC"
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        query = f"SELECT id, username, content, timestamp FROM messages ORDER BY timestamp {order_clause} LIMIT ? OFFSET ?"
        cursor.execute(query, (limit, offset))
        messages = cursor.fetchall()
    
    from jinja2 import Template
    template = Template(HTML_TEMPLATE)
    return template.render(request=request, messages=messages)

@app.post("/messages")
async def post_message(message: Message):
    if not message.username or not message.content:
        raise HTTPException(status_code=400, detail="Invalid input")
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO messages (username, content) VALUES (?, ?)", 
                (message.username, message.content)
            )
            conn.commit()
        return {"status": "Successful operation"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)