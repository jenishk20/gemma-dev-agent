import sqlite3
import os
from typing import Optional, List
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field
import uvicorn
from jinja2 import Template, escape

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

# Pydantic Model with basic resource exhaustion bounds
class Message(BaseModel):
    content: str = Field(..., max_length=10000)
    username: str = Field(..., max_length=255)

# FastAPI App
app = FastAPI(title="MyForum")

# HTML Template with Jinja2 auto-escaping (handled via Template.render or explicit escape)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>MyForum</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f4f4f9; }
        .message { background: white; padding: 10px; margin-bottom: 10px; border-radius: 5px; border: 1px solid #ddd; }
        .username { font-weight: bold; color: #555; }
        .content { margin-top: 5px; white-space: pre-wrap; }
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
            <input type="text" name="username" placeholder="Username" required maxlength="255">
            <textarea name="content" placeholder="Message content" required maxlength="10000"></textarea>
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
    # 1. Validate sort enum to prevent SQL injection via ORDER BY (which cannot be parameterized)
    if sort.upper() not in ["ASC", "DESC"]:
        sort = "DESC"
    else:
        sort = sort.upper()

    # 2. Bound resource exhaustion for limit/offset
    limit = max(0, min(limit, 100))
    offset = max(0, offset)

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # Use parameterized queries for limit and offset
            query = f"SELECT id, username, content, timestamp FROM messages ORDER BY timestamp {sort} LIMIT ? OFFSET ?"
            cursor.execute(query, (limit, offset))
            messages = cursor.fetchall()
    except Exception:
        # Generic error to avoid leaking internal DB details
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    # 3. Prevent XSS: Jinja2 Template renders variables as escaped by default.
    # We use the Template object which handles escaping.
    template = Template(HTML_TEMPLATE)
    return template.render(request=request, messages=messages)

@app.post("/messages")
async def post_message(request: Request):
    content_type = request.headers.get('content-type', '')
    
    try:
        if 'application/json' in content_type:
            # Bound request size for JSON
            body = await request.body()
            if len(body) > 100000: # 100KB limit
                raise HTTPException(status_code=400, detail="Request body too large")
            
            import json
            data = json.loads(body)
            msg = Message(**data)
        else:
            # Handle form submission
            form_data = await request.form()
            username = form_data.get("username")
            content = form_data.get("content")
            if not username or not content:
                raise HTTPException(status_code=400, detail="Invalid input")
            
            # Validate lengths for form data to prevent resource exhaustion
            if len(username) > 255 or len(content) > 10000:
                raise HTTPException(status_code=400, detail="Input too long")
                
            msg = Message(username=username, content=content)

        # 4. Prevent SQL Injection: Use parameterized queries
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT INTO messages (username, content) VALUES (?, ?)", (msg.username, msg.content))
            conn.commit()
        
        if 'application/json' not in content_type:
            return RedirectResponse(url="/messages", status_code=303)
            
        return {"status": "Successful operation"}

    except (ValueError, TypeError, HTTPException) as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail="Invalid input")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")

if __name__ == "__main__":
    init_db()
    uvicorn.run(app, host="0.0.0.0", port=5000)