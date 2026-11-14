import os
import sqlite3
from flask import Flask, request, render_template_string, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key_for_dev")

DB_PATH = "db.sqlite3"

# HTML Template for the forum
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>MyForum</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .message { border-bottom: 1px solid #ccc; padding: 10px 0; }
        .username { font-weight: bold; color: #555; }
        .content { margin-top: 5px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; }
        input, textarea { width: 100%; padding: 8px; box-sizing: border-box; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; }
    </style>
</head>
<body>
    <h1>MyForum</h1>
    
    <div style="background: #f9f9f9; padding: 15px; border-radius: 5px; margin-bottom: 30px;">
        <h3>Post a Message</h3>
        <form action="/messages" method="POST">
            <div class="form-group">
                <label>Username:</label>
                <input type="text" name="username" required>
            </div>
            <div class="form-group">
                <label>Message:</label>
                <textarea name="content" required></textarea>
            </div>
            <button type="submit">Post</button>
        </form>
    </div>

    <h3>Messages</h3>
    <div>
        {% for msg in messages %}
            <div class="message">
                <span class="username">{{ msg.username }}</span>
                <div class="content">{{ msg.content }}</div>
            </div>
        {% else %}
            <p>No messages yet.</p>
        {% endfor %}
    </div>
    
    <div style="margin-top: 20px;">
        <a href="/messages?sort=ASC">Oldest First</a> | 
        <a href="/messages?sort=DESC">Newest First</a>
    </div>
</body>
</html>
"""

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

@app.route('/messages', methods=['GET'])
def get_messages():
    # Extract query parameters with defaults as per OpenAPI spec
    try:
        limit = int(request.args.get('limit', 10))
        offset = int(request.args.get('offset', 0))
        sort = request.args.get('sort', 'DESC').upper()
    except ValueError:
        return "Invalid parameter type", 400

    if sort not in ['ASC', 'DESC']:
        sort = 'DESC'

    conn = get_db_connection()
    # Use parameterized query to prevent SQL injection
    query = f"SELECT username, content FROM messages ORDER BY timestamp {sort} LIMIT ? OFFSET ?"
    messages_rows = conn.execute(query, (limit, offset)).fetchall()
    conn.close()

    # Convert rows to list of dicts for the template
    messages = [{"username": row["username"], "content": row["content"]} for row in messages_rows]
    
    return render_template_string(HTML_TEMPLATE, messages=messages)

@app.route('/messages', methods=['POST'])
def post_message():
    # The OpenAPI spec allows application/json, but for a webapp we handle both JSON and Form data
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form

    username = data.get('username')
    content = data.get('content')

    if not username or not content:
        return "Invalid input: username and content are required", 400

    # Basic sanitization is handled by Jinja2's auto-escaping in the template
    conn = get_db_connection()
    conn.execute("INSERT INTO messages (username, content) VALUES (?, ?)", (username, content))
    conn.commit()
    conn.close()

    # Redirect back to the message list
    return "Message posted successfully", 200

if __name__ == '__main__':
    init_db()
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000, debug=False)