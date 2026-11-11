import os
import sqlite3
from flask import Flask, request, render_template_string, jsonify, redirect

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key")

DB_NAME = "db.sqlite3"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

# HTML Template for the forum
# Using Jinja2's auto-escaping (via render_template_string) to prevent XSS.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>MyForum</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .message { border-bottom: 1px solid #ccc; padding: 10px 0; }
        .username { font-weight: bold; color: #333; }
        .content { margin-top: 5px; white-space: pre-wrap; }
        .form-box { background: #f4f4f4; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        input, textarea { display: block; width: 100%; margin-bottom: 10px; }
    </style>
</head>
<body>
    <h1>MyForum</h1>
    
    <div class="form-box">
        <h3>Post a Message</h3>
        <form action="/messages" method="post">
            <input type="text" name="username" placeholder="Username" required maxlength="100">
            <textarea name="content" placeholder="Message content" required maxlength="5000"></textarea>
            <button type="submit">Post</button>
        </form>
    </div>

    <div class="messages">
        <h3>Messages</h3>
        {% for msg in messages %}
            <div class="message">
                <span class="username">{{ msg.username }}</span>
                <div class="content">{{ msg.content }}</div>
            </div>
        {% endfor %}
    </div>
    
    <div style="margin-top: 20px;">
        <a href="/messages?sort=ASC">Oldest First</a> | 
        <a href="/messages?sort=DESC">Newest First</a>
    </div>
</body>
</html>
"""

@app.route('/messages', methods=['GET'])
def get_messages():
    try:
        # Resource Exhaustion: Bound the limit to a maximum of 100
        limit = request.args.get('limit', default=10, type=int)
        if limit < 0: limit = 0
        if limit > 100: limit = 100
        
        offset = request.args.get('offset', default=0, type=int)
        if offset < 0: offset = 0
        if offset > 10000: offset = 10000 # Prevent extreme offsets

        sort = request.args.get('sort', default='DESC').upper()
        # SQL Injection prevention: Use a strict whitelist for the ORDER BY clause
        # since parameters cannot be used for identifiers/keywords like ASC/DESC.
        if sort not in ['ASC', 'DESC']:
            sort = 'DESC'

        with get_db() as conn:
            # Use parameterized queries for limit and offset
            query = f"SELECT username, content FROM messages ORDER BY timestamp {sort} LIMIT ? OFFSET ?"
            messages = conn.execute(query, (limit, offset)).fetchall()
        
        msgs_list = [dict(row) for row in messages]
        return render_template_string(HTML_TEMPLATE, messages=msgs_list)
    except Exception:
        # Error handling: Return 500 without leaking internal details
        return "Internal Server Error", 500

@app.route('/messages', methods=['POST'])
def post_message():
    try:
        # Resource Exhaustion: Limit request body size (Flask does this via MAX_CONTENT_LENGTH, 
        # but we check specifically for the JSON/Form data here).
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form

        if not data:
            return jsonify({"error": "Invalid input"}), 400

        username = data.get('username')
        content = data.get('content')

        # Input Validation: Ensure fields are strings and not empty
        if not isinstance(username, str) or not isinstance(content, str):
            return jsonify({"error": "Invalid input"}), 400
        
        username = username.strip()
        content = content.strip()

        if not username or not content:
            return jsonify({"error": "Invalid input"}), 400
        
        # Resource Exhaustion: Prevent excessively large database entries
        if len(username) > 100 or len(content) > 5000:
            return jsonify({"error": "Invalid input"}), 400

        with get_db() as conn:
            # SQL Injection prevention: Use parameterized API
            conn.execute("INSERT INTO messages (username, content) VALUES (?, ?)", (username, content))
            conn.commit()

        if not request.is_json:
            return redirect('/messages')
        
        return jsonify({"status": "Successful operation"}), 200
    except Exception:
        # Error handling: Return documented error status codes
        return jsonify({"error": "Invalid input"}), 400

if __name__ == '__main__':
    # Limit the size of the request body to prevent DoS
    app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024 # 1MB
    init_db()
    app.run(host='0.0.0.0', port=5000)