import sqlite3
import os
from typing import Optional, List
from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

# Configuration
DB_FILE = "db.sqlite3"
APP_SECRET = os.getenv("APP_SECRET", "default_secret")

app = FastAPI(title="MyForum")
templates = Jinja2Templates(directory=".") # We will use a string template for simplicity since we must keep everything in one file

# Pydantic Model
class Message(BaseModel):
    content: str
    username: str

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

# HTML Template as a string to avoid external file dependencies
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>MyForum</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background-color: #f4f4f9; }
        .message { background: white; padding: 15px; margin-bottom: 10px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .username { font-weight: bold; color: #333; }
        .content { margin-top: 5px; }
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
        <!-- Hidden input to make it send JSON via JS or just use standard form -->
        <script>
            document.getElementById('msgForm').onsubmit = async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                const data = {
                    username: formData.get('username'),
                    content: formData.get('content')
                };
                const res = await fetch('/messages', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                if (res.ok) { window.location.reload(); } else { alert('Error posting message'); }
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
    if sort not in ["ASC", "DESC"]:
        sort = "DESC"
    
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        query = f"SELECT id, username, content, timestamp FROM messages ORDER BY timestamp {sort} LIMIT ? OFFSET ?"
        cursor.execute(query, (limit, offset))
        messages = cursor.fetchall()

    from jinja2 import Template
    template = Template(HTML_TEMPLATE)
    return template.render(messages=messages, limit=limit, offset=offset, sort=sort)

@app.post("/messages")
async def post_message(msg: Message):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("INSERT INTO messages (username, content) VALUES (?, ?)", (msg.username, msg.content))
            conn.commit()
        return {"status": "Successful operation"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)