import os
import sqlite3
from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

# Configuration
DB_FILE = "db.sqlite3"
PORT = 5000
HOST = "0.0.0.0"

app = FastAPI(title="MyForum")
templates = Jinja2Templates(directory=".") # Templates will be rendered from strings or inline

# Pydantic Model for Request Body
class Message(BaseModel):
    content: str
    username: str

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
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>MyForum</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f4f4f4; }
        .message { background: white; padding: 15px; margin-bottom: 10px; border-radius: 5px; border: 1px solid #ddd; }
        .username { font-weight: bold; color: #333; }
        .content { margin-top: 5px; }
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
            <input type="text" name="username" placeholder="Username" required>
            <textarea name="content" placeholder="Message content" required></textarea>
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
        // Handle form submission via JS to match the JSON API requirement of the schema
        document.getElementById('msgForm').onsubmit = async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = {
                username: formData.get('username'),
                content: formData.get('content')
            };
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
    # Validate sort enum
    if sort.upper() not in ["ASC", "DESC"]:
        sort = "DESC"
    
    order_clause = "DESC" if sort.upper() == "DESC" else "ASC"
    
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        query = f"SELECT id, username, content, timestamp FROM messages ORDER BY timestamp {order_clause} LIMIT ? OFFSET ?"
        cursor.execute(query, (limit, offset))
        messages = cursor.fetchall()

    # We use Jinja2 to render the HTML string
    from jinja2 import Template
    template = Template(HTML_TEMPLATE)
    return template.render(messages=messages)

@app.post("/messages")
async def post_message(msg: Message):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute(
                "INSERT INTO messages (username, content) VALUES (?, ?)", 
                (msg.username, msg.content)
            )
            conn.commit()
        return {"status": "Successful operation"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)