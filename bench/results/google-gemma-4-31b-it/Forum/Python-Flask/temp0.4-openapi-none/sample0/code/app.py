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

# HTML Template for the forum
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
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
        <form action="/messages" method="post" id="postForm">
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
        <a href="?limit={{ limit }}&offset={{ offset - limit if offset > 0 else 0 }}&sort={{ sort }}">Previous</a> | 
        <a href="?limit={{ limit }}&offset={{ offset + limit }}&sort={{ sort }}">Next</a>
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

    conn = get_db_connection()
    query = f"SELECT username, content, timestamp FROM messages ORDER BY timestamp {sort} LIMIT ? OFFSET ?"
    messages = conn.execute(query, (limit, offset)).fetchall()
    conn.close()

    return render_template_string(
        HTML_TEMPLATE, 
        messages=messages, 
        limit=limit, 
        offset=offset, 
        sort=sort
    )

@app.route('/messages', methods=['POST'])
def post_message():
    # The OpenAPI schema specifies application/json
    data = request.get_json()
    
    # Handle cases where form-data might be sent instead of JSON for convenience in browser
    if data is None:
        # Fallback for the HTML form submission
        username = request.form.get('username')
        content = request.form.get('content')
    else:
        username = data.get('username')
        content = data.get('content')

    if not username or not content:
        return jsonify({"error": "Invalid input"}), 400

    conn = get_db_connection()
    conn.execute('INSERT INTO messages (username, content) VALUES (?, ?)', (username, content))
    conn.commit()
    conn.close()

    # If it was a JSON request, return 200. If it was a form, redirect back to view.
    if request.content_type == 'application/json':
        return jsonify({"status": "Successful operation"}), 200
    else:
        from flask import redirect, url_for
        return redirect(url_for('get_messages'))

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)