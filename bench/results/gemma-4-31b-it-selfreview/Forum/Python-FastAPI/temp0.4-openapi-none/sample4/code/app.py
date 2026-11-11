import sqlite3
import os
from typing import Optional, List
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import uvicorn
from jinja2 import Template, escape

# --- Models ---
class Message(BaseModel):
    # Added constraints to prevent resource exhaustion (extremely large strings)
    content: str = Field(..., max_length=10000)
    username: str = Field(..., max_length=255)

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

# --- App Initialization ---
app = FastAPI(title="MyForum")

# HTML Template
# Note: Jinja2's Template.render() does not automatically escape variables 
# unless we use the environment's autoescape or explicitly call escape().
# We will use explicit escaping for user-generated content.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>MyForum</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f4f4f4; }
        .message { background: white; padding: 10px; margin-bottom: 10px; border-radius: 5px; border: 1px solid #ddd; }
        .username { font-weight: bold; color: #333; }
        .content { margin-top: 5px; white-space: pre-wrap; }
        .form-box { background: white; padding: 20px; border-radius: 5px; border: 1px solid #ddd; margin-bottom: 20px; }
        input, textarea { display: block; width: 100%; margin-bottom: 10px; padding: 8px; box-sizing: border-box; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; }
    </style>
</head>
<body>
    <h1>MyForum</h1>
    <div class="form-box">
        <h3>Post a Message</h3>
        <form action="/messages" method="post" id="msgForm">
            <input type="text" name="username" placeholder="Username" required maxlength="255">
            <textarea name="content" placeholder="Message content" required maxlength="10000"></textarea>
            <button type="submit">Post</button>
        </form>
    </div>
    <div id="messages">
        {% for msg in messages %}
        <div class="message">
            <span class="username">{{ msg.username }}</span> <small>{{ msg.timestamp }}</small>
            <div class="content">{{ msg.content }}</div>
        </div>
        {% endfor %}
    </div>
    <script>
        document.getElementById('msgForm').onsubmit = async function(e) {
            e.preventDefault();
            const formData = new FormData(this);
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
                    location.reload();
                } else {
                    alert('Error posting message');
                }
            } catch (err) {
                alert('Network error');
            }
        };
    </script>
</body>
</html>
"""

# --- Routes ---

@app.get("/messages", response_class=HTMLResponse)
async def get_messages(
    request: Request, 
    limit: int = 10, 
    offset: int = 0, 
    sort: str = "DESC"
):
    # 1. Resource Exhaustion: Bound the limit to prevent DoS via massive result sets
    safe_limit = min(max(1, limit), 100)
    safe_offset = max(0, offset)
    
    # 2. SQL Injection: 'sort' is used in the ORDER BY clause where parameters (?) cannot be used.
    # We strictly validate against a whitelist.
    sort_upper = sort.upper()
    if sort_upper not in ["ASC", "DESC"]:
        order_clause = "DESC"
    else:
        order_clause = sort_upper

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # Use parameterized queries for limit and offset
            query = f"SELECT username, content, timestamp FROM messages ORDER BY timestamp {order_clause} LIMIT ? OFFSET ?"
            cursor.execute(query, (safe_limit, safe_offset))
            rows = cursor.fetchall()
            
            # Prepare data for template with explicit HTML escaping to prevent XSS
            messages_data = []
            for row in rows:
                messages_data.append({
                    "username": escape(row[0]),
                    "content": escape(row[1]),
                    "timestamp": escape(row[2])
                })
    except Exception:
        # Error handling: Return generic error or 500 without leaking internals
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    template = Template(HTML_TEMPLATE)
    return template.render(messages=messages_data)

@app.post("/messages")
async def post_message(msg: Message):
    # Pydantic handles basic type validation and length constraints defined in the model.
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            # SQL Injection prevention: Use parameterized query
            conn.execute(
                "INSERT INTO messages (username, content) VALUES (?, ?)", 
                (msg.username, msg.content)
            )
            conn.commit()
    except Exception:
        # Error handling: Return 400 as per OpenAPI spec for invalid/failed input
        raise HTTPException(status_code=400, detail="Invalid input")
    
    return {"status": "Successful operation"}

# --- Startup ---
@app.on_event("startup")
def on_startup():
    init_db()

if __name__ == "__main__":
    # Port 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)