import os
import sqlite3
from flask import Flask, request, render_template_string, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key")

DB_NAME = "db.sqlite3"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

# HTML Template for the forum frontend
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>MyForum</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .message { border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; border-radius: 5px; }
        .username { font-weight: bold; color: #555; }
        .form-group { margin-bottom: 15px; }
        input, textarea { width: 100%; padding: 8px; margin-top: 5px; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; }
    </style>
</head>
<body>
    <h1>MyForum</h1>
    
    <div style="background: #f9f9f9; padding: 20px; border-radius: 10px; margin-bottom: 30px;">
        <h3>Post a Message</h3>
        <form action="/messages" method="post" id="postForm">
            <div class="form-group">
                <label>Username:</label><br>
                <input type="text" name="username" required>
            </div>
            <div class="form-group">
                <label>Message:</label><br>
                <textarea name="content" rows="3" required></textarea>
            </div>
            <button type="submit">Post</button>
        </form>
        <p id="apiNote" style="font-size: 0.8em; color: #666;">Note: This form sends as standard form data for convenience, but the API accepts JSON.</p>
    </div>

    <hr>
    <h3>Messages</h3>
    <div id="messages">
        {% for msg in messages %}
            <div class="message">
                <span class="username">{{ msg.username }}</span> 
                <small style="color: #999;">{{ msg.timestamp }}</small>
                <p>{{ msg.content }}</p>
            </div>
        {% endfor %}
    </div>
</body>
</html>
"""

@app.route('/messages', methods=['GET'])
def get_messages():
    # Parameters from OpenAPI schema
    limit = request.args.get('limit', 10, type=int)
    offset = request.args.get('offset', 0, type=int)
    sort = request.args.get('sort', 'DESC').upper()

    if sort not in ['ASC', 'DESC']:
        sort = 'DESC'

    order_clause = f"ORDER BY timestamp {sort}"
    
    with get_db_connection() as conn:
        messages = conn.execute(
            f"SELECT username, content, timestamp FROM messages {order_clause} LIMIT ? OFFSET ?", 
            (limit, offset)
        ).fetchall()

    # The schema specifies text/html response
    return render_template_string(HTML_TEMPLATE, messages=messages)

@app.route('/messages', methods=['POST'])
def post_message():
    # The OpenAPI schema specifies application/json
    if request.is_json:
        data = request.get_json()
    else:
        # Fallback for HTML form submission to make the webapp usable via browser
        data = request.form

    username = data.get('username')
    content = data.get('content')

    if not username or not content:
        return jsonify({"error": "Invalid input"}), 400

    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO messages (username, content) VALUES (?, ?)", 
            (username, content)
        )
        conn.commit()

    # If it was a form submission, redirect back to the list
    if not request.is_json:
        from flask import redirect
        return redirect('/messages')

    return jsonify({"status": "Successful operation"}), 200

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)