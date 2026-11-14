import os
import sqlite3
from flask import Flask, request, render_template_string, jsonify, redirect, url_for

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

# HTML Template for the forum
# Using Jinja2's auto-escaping for content and usernames to prevent XSS.
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
        .content { margin-top: 5px; }
        .form-section { margin-bottom: 30px; padding: 20px; background: #f9f9f9; border-radius: 5px; }
        input, textarea { display: block; margin-bottom: 10px; width: 100%; padding: 8px; box-sizing: border-box; }
        button { padding: 10px 20px; cursor: pointer; }
        .pagination { margin-top: 20px; }
    </style>
</head>
<body>
    <h1>MyForum</h1>
    
    <div class="form-section">
        <h3>Post a Message</h3>
        <form action="/messages" method="post">
            <input type="text" name="username" placeholder="Username" required>
            <textarea name="content" placeholder="Message content" required></textarea>
            <button type="submit">Post Message</button>
        </form>
    </div>

    <h2>Messages</h2>
    <div id="messages">
        {% for msg in messages %}
        <div class="message">
            <span class="username">{{ msg.username }}</span> 
            <small style="color: #999;">{{ msg.timestamp }}</small>
            <div class="content">{{ msg.content }}</div>
        </div>
        {% endfor %}
    </div>

    <div class="pagination">
        <a href="{{ url_for('get_messages', limit=limit, offset=prev_offset, sort=sort) }}">Previous</a> | 
        <a href="{{ url_for('get_messages', limit=limit, offset=next_offset, sort=sort) }}">Next</a>
    </div>
</body>
</html>
"""

@app.route('/messages', methods=['GET'])
def get_messages():
    try:
        # Validate and bound query parameters to prevent resource exhaustion (DoS)
        limit = request.args.get('limit', 10, type=int)
        if limit < 1 or limit > 100:
            limit = 10
            
        offset = request.args.get('offset', 0, type=int)
        if offset < 0:
            offset = 0
            
        sort = request.args.get('sort', 'DESC').upper()
        if sort not in ['ASC', 'DESC']:
            sort = 'DESC'

        conn = get_db_connection()
        # SQL Injection Prevention: 
        # 'sort' is validated against a whitelist (ASC/DESC), so it is safe to interpolate.
        # limit and offset are passed as parameterized values.
        query = f"SELECT username, content, timestamp FROM messages ORDER BY timestamp {sort} LIMIT ? OFFSET ?"
        messages = conn.execute(query, (limit, offset)).fetchall()
        conn.close()

        prev_offset = max(0, offset - limit)
        next_offset = offset + limit

        return render_template_string(
            HTML_TEMPLATE, 
            messages=messages, 
            limit=limit, 
            offset=offset, 
            prev_offset=prev_offset,
            next_offset=next_offset, 
            sort=sort
        )
    except Exception:
        # Generic error handling to prevent leaking stack traces
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/messages', methods=['POST'])
def post_message():
    try:
        # Resource exhaustion: limit request body size (Flask does this via MAX_CONTENT_LENGTH, 
        # but we can also check the data size here)
        if request.content_length and request.content_length > 1 * 1024 * 1024: # 1MB limit
            return jsonify({"error": "Request entity too large"}), 400

        # The OpenAPI schema specifies application/json
        if request.content_type == 'application/json':
            data = request.get_json(silent=True)
            if data is None:
                return jsonify({"error": "Invalid JSON"}), 400
            username = data.get('username')
            content = data.get('content')
        else:
            # Fallback for HTML form submission
            username = request.form.get('username')
            content = request.form.get('content')

        # Validate input presence and types
        if not isinstance(username, str) or not isinstance(content, str) or not username.strip() or not content.strip():
            return jsonify({"error": "Invalid input"}), 400

        # SQL Injection Prevention: Use parameterized queries
        conn = get_db_connection()
        conn.execute('INSERT INTO messages (username, content) VALUES (?, ?)', (username, content))
        conn.commit()
        conn.close()

        if request.content_type == 'application/json':
            return jsonify({"status": "Successful operation"}), 200
        else:
            return redirect(url_for('get_messages'))
            
    except Exception:
        # Generic error handling to prevent leaking stack traces
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == '__main__':
    # Set a reasonable limit for request bodies to prevent memory exhaustion
    app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024 
    init_db()
    app.run(host='0.0.0.0', port=5000)