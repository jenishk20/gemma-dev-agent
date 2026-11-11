import sqlite3
import os
from typing import Optional, List
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

# --- Models ---
class Message(BaseModel):
    content: str
    username: str

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
templates = Jinja2Templates(directory=".") # We will use a string template for simplicity in one file

# Since we must put everything in one file and cannot create a 'templates' folder, 
# we will define a simple HTML template string and use Jinja2's Template class directly.
from jinja2 import Template

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>MyForum</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f4f4f4; }
        .message { background: white; padding: 10px; margin-bottom: 10px; border-radius: 5px; border: 1px solid #ddd; }
        .username { font-weight: bold; color: #333; }
        .content { margin-top: 5px; }
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
            <input type="text" name="username" placeholder="Username" required>
            <textarea name="content" placeholder="Message content" required></textarea>
            <button type="submit" onclick="submitPost()">Post</button>
        </form>
    </div>
    <div id="messages">
        {% for msg in messages %}
        <div class="message">
            <span class="username">{{ msg[1] }}</span> <small>{{ msg[4] }}</small>
            <div class="content">{{ msg[2] }}</div>
        </div>
        {% endfor %}
    </div>
    <script>
        async function submitPost() {
            const form = document.getElementById('msgForm');
            const formData = new FormData(form);
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
                location.reload();
            } else {
                alert('Error posting message');
            }
        }
        // Override form default submit to use our JS function
        document.getElementById('msgForm').onsubmit = function(e) {
            e.preventDefault();
            submitPost();
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
    # Validate sort enum
    if sort.upper() not in ["ASC", "DESC"]:
        sort = "DESC"
    
    order_clause = "DESC" if sort.upper() == "DESC" else "ASC"
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # We select timestamp as well for the template
        query = f"SELECT * FROM messages ORDER BY timestamp {order_clause} LIMIT ? OFFSET ?"
        cursor.execute(query, (limit, offset))
        messages = cursor.fetchall()
    
    template = Template(HTML_TEMPLATE)
    return template.render(messages=messages)

@app.post("/messages")
async def post_message(msg: Message):
    if not msg.username or not msg.content:
        raise HTTPException(status_code=400, detail="Invalid input")
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO messages (username, content) VALUES (?, ?)", 
                (msg.username, msg.content)
            )
            conn.commit()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {"status": "Successful operation"}

# --- Startup ---
@app.on_event("startup")
def on_startup():
    init_db()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)