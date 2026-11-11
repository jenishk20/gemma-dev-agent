import os
import sqlite3
from flask import Flask, request, render_template_string, jsonify, redirect

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
# Jinja2 automatically escapes variables ({{ msg.username }}), preventing XSS.
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
        .form-group { margin-bottom: 15px; }
        input, textarea { width: 100%; padding: 8px; margin-top: 5px; box-sizing: border-box; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; }
    </style>
</head>
<body>
    <h1>MyForum</h1>
    
    <div style="background: #f9f9f9; padding: 20px; border-radius: 10px; margin-bottom: 30px;">
        <h3>Post a Message</h3>
        <form action="/messages" method="post" id="postForm">
            <div class="form-group">
                <label for="username">Username:</label><br>
                <input type="text" id="username" name="username" required>
            </div>
            <div class="form-group">
                <label for="content">Message:</label><br>
                <textarea id="content" name="content" rows="3" required></textarea>
            </div>
            <button type="submit">Post</button>
        </form>
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
    try:
        # Resource Exhaustion: Bound the limit to prevent DoS via massive result sets
        limit = request.args.get('limit', 10, type=int)
        if limit < 1 or limit > 100:
            limit = 10
            
        offset = request.args.get('offset', 0, type=int)
        if offset < 0:
            offset = 0

        # SQL Injection prevention: 'sort' is an enum. 
        # We strictly validate against the allowed list and do not interpolate raw input.
        sort_input = request.args.get('sort', 'DESC').upper()
        sort_direction = "ASC" if sort_input == "ASC" else "DESC"

        # Use parameterized queries for limit and offset.
        # The sort direction is hard-coded to one of two safe strings.
        query = f"SELECT username, content, timestamp FROM messages ORDER BY timestamp {sort_direction} LIMIT ? OFFSET ?"
        
        with get_db_connection() as conn:
            messages = conn.execute(query, (limit, offset)).fetchall()

        return render_template_string(HTML_TEMPLATE, messages=messages)
    except Exception:
        # Error handling: Return a generic 500 without leaking stack traces
        return "Internal Server Error", 500

@app.route('/messages', methods=['POST'])
def post_message():
    try:
        # Resource Exhaustion: Limit request body size (Flask does this via MAX_CONTENT_LENGTH, 
        # but we check for JSON presence specifically)
        if request.is_json:
            data = request.get_json(silent=True)
            if data is None:
                return jsonify({"error": "Invalid JSON"}), 400
        else:
            data = request.form

        if not data:
            return jsonify({"error": "Invalid input"}), 400

        username = data.get('username')
        content = data.get('content')

        # Validation: Ensure inputs are strings and not empty
        if not isinstance(username, str) or not isinstance(content, str):
            return jsonify({"error": "Invalid input"}), 400
        
        if not username.strip() or not content.strip():
            return jsonify({"error": "Invalid input"}), 400

        # SQL Injection prevention: Use parameterized query
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO messages (username, content) VALUES (?, ?)", 
                (username, content)
            )
            conn.commit()

        if not request.is_json:
            return redirect('/messages')

        return jsonify({"status": "Successful operation"}), 200
    except Exception:
        # Error handling: Return documented error status codes
        return jsonify({"error": "Invalid input"}), 400

if __name__ == '__main__':
    # Set a reasonable limit for request body size to prevent resource exhaustion
    app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1MB
    init_db()
    app.run(host='0.0.0.0', port=5000)