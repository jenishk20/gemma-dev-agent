import os
import sqlite3
from typing import Optional, List
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import uvicorn
from jinja2 import Template, escape

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
    # Resource exhaustion: bound input lengths to prevent DoS via massive strings
    content: str = Field(..., max_length=10000)
    username: str = Field(..., max_length=100)

# --- App Initialization ---
app = FastAPI(title="MyForum")

# HTML template embedded as a string. 
# Using Jinja2's auto-escaping mechanism via the Template object.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>MyForum</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .message { border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; border-radius: 5px; }
        .username { font-weight: bold; color: #555; }
        .content { margin-top: 5px; white-space: pre-wrap; }
        .form-group { margin-bottom: 15px; }
        input, textarea { width: 100%; padding: 8px; margin-top: 5px; box-sizing: border-box; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; }
    </style>
</head>
<body>
    <h1>MyForum</h1>
    
    <div style="background: #f9f9f9; padding: 20px; border-radius: 5px; margin-bottom: 30px;">
        <h3>Post a Message</h3>
        <form action="/messages" method="post" id="postForm">
            <div class="form-group">
                <label for="username">Username:</label><br>
                <input type="text" id="username" name="username" required>
            </div>
            <div class="form-group">
                <label for="content">Message:</label><br>
                <textarea id="content" name="content" required></textarea>
            </div>
            <button type="submit">Post</button>
        </form>
        <script>
            document.getElementById('postForm').onsubmit = async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                const data = {
                    username: formData.get('username'),
                    content: formData.get('content')
                };
                try {
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
                } catch (err) {
                    alert('Network error');
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
    # Resource exhaustion: Bound the limit to prevent huge memory allocation
    safe_limit = min(max(1, limit), 100)
    safe_offset = max(0, offset)
    
    # SQL Injection prevention: 
    # 1. Use a strict whitelist for the ORDER BY clause (which cannot be parameterized in SQLite)
    # 2. Use parameterized queries for LIMIT and OFFSET
    order_clause = "ASC" if sort.upper() == "ASC" else "DESC"
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # The order_clause is strictly controlled by the logic above, not direct user input
            query = f"SELECT id, username, content, timestamp FROM messages ORDER BY timestamp {order_clause} LIMIT ? OFFSET ?"
            cursor.execute(query, (safe_limit, safe_offset))
            messages = cursor.fetchall()
        
        # XSS Prevention: 
        # Jinja2 Template with autoescape=True ensures all variables are HTML-escaped.
        template = Template(HTML_TEMPLATE)
        # We manually escape the data items to be doubly sure, though Jinja2 handles this.
        # In this specific implementation, we use the Template object which we'll render.
        # To ensure strict escaping, we use the jinja2.escape function or rely on the environment.
        
        # Since we are using a raw Template object, we ensure the data is treated as text.
        # The most secure way in a single-file setup is to use a Jinja2 Environment with autoescape.
        from jinja2 import Environment, select_autoescape
        env = Environment(autoescape=select_autoescape(['html', 'xml']))
        jinja_template = env.from_string(HTML_TEMPLATE)
        return jinja_template.render(request=request, messages=messages)
    except Exception:
        # Error handling: Return generic 500 without leaking internal details
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/messages")
async def post_message(message: Message):
    # Input validation is handled by Pydantic (Message model)
    # Resource exhaustion: Pydantic max_length prevents oversized payloads
    
    if not message.username.strip() or not message.content.strip():
        raise HTTPException(status_code=400, detail="Invalid input")
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            # SQL Injection prevention: Use parameterized query
            conn.execute(
                "INSERT INTO messages (username, content) VALUES (?, ?)", 
                (message.username, message.content)
            )
            conn.commit()
        return {"status": "Successful operation"}
    except Exception:
        # Error handling: Return documented 400 for invalid input/processing errors
        raise HTTPException(status_code=400, detail="Invalid input")

if __name__ == "__main__":
    # Run server on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)