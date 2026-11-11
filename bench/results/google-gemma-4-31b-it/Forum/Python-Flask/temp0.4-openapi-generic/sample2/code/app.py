import os
import sqlite3
from flask import Flask, request, render_template_string, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key_for_dev")

DB_NAME = "db.sqlite3"

def get_db():
    """Connects to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema."""
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
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>MyForum</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .message { border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; border-radius: 5px; }
        .username { font-weight: bold; color: #333; }
        .content { margin-top: 5px; }
        .form-group { margin-bottom: 15px; }
        input, textarea { width: 100%; padding: 8px; margin-top: 5px; box-sizing: border-box; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; }
        .pagination { margin-top: 20px; }
    </style>
</head>
<body>
    <h1>MyForum</h1>
    
    <div style="background: #f9f9f9; padding: 15px; border-radius: 5px; margin-bottom: 30px;">
        <h3>Post a Message</h3>
        <form action="/messages" method="POST">
            <div class="form-group">
                <label>Username:</label><br>
                <input type="text" name="username" required>
            </div>
            <div class="form-group">
                <label>Message:</label><br>
                <textarea name="content" rows="3" required></textarea>
            </div>
            <button type="submit">Post Message</button>
        </form>
    </div>

    <h2>Messages</h2>
    {% for msg in messages %}
        <div class="message">
            <span class="username">{{ msg.username }}</span> 
            <small style="color: gray;">{{ msg.timestamp }}</small>
            <div class="content">{{ msg.content }}</div>
        </div>
    {% else %}
        <p>No messages yet.</p>
    {% endfor %}

    <div class="pagination">
        {% if offset > 0 %}
            <a href="{{ url_for('get_messages', offset=offset-limit, sort=sort) }}">« Previous</a>
        {% endif %}
        <a href="{{ url_for('get_messages', offset=offset+limit, sort=sort) }}">Next »</a>
    </div>
</body>
</html>
"""

@app.route('/messages', methods=['GET'])
def get_messages():
    # Parameters from OpenAPI schema
    try:
        limit = int(request.args.get('limit', 10))
        offset = int(request.args.get('offset', 0))
        sort = request.args.get('sort', 'DESC').upper()
    except ValueError:
        return "Invalid parameter type", 400

    if sort not in ['ASC', 'DESC']:
        sort = 'DESC'

    with get_db() as conn:
        # Use parameterized query to prevent SQL injection
        query = f"SELECT username, content, timestamp FROM messages ORDER BY timestamp {sort} LIMIT ? OFFSET ?"
        cursor = conn.execute(query, (limit, offset))
        messages = cursor.fetchall()

    return render_template_string(
        HTML_TEMPLATE, 
        messages=messages, 
        limit=limit, 
        offset=offset, 
        sort=sort
    )

@app.route('/messages', methods=['POST'])
def post_message():
    # Support both JSON (as per OpenAPI) and Form data (for the HTML UI)
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form

    username = data.get('username')
    content = data.get('content')

    if not username or not content:
        return jsonify({"error": "Invalid input: username and content are required"}), 400

    with get_db() as conn:
        conn.execute("INSERT INTO messages (username, content) VALUES (?, ?)", (username, content))
        conn.commit()

    # If it was a form request, redirect back to the list
    if not request.is_json:
        from flask import redirect
        return redirect('/messages')
    
    return jsonify({"status": "Successful operation"}), 200

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)