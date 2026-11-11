import os
import sqlite3
from flask import Flask, request, render_template_string, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key_for_dev")

DB_FILE = "db.sqlite3"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
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
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f4f4f9; }
        .message { background: white; padding: 15px; margin-bottom: 10px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .username { font-weight: bold; color: #333; }
        .content { margin-top: 5px; color: #666; }
        .form-group { margin-bottom: 15px; }
        input, textarea { width: 100%; padding: 8px; margin-top: 5px; box-sizing: border-box; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; border-radius: 3px; }
        .controls { margin-bottom: 20px; display: flex; gap: 10px; align-items: center; }
    </style>
</head>
<body>
    <h1>MyForum</h1>
    
    <div style="background: #eee; padding: 20px; border-radius: 5px; margin-bottom: 30px;">
        <h3>Post a Message</h3>
        <form action="/messages" method="POST" id="postForm">
            <div class="form-group">
                <label>Username:</label><br>
                <input type="text" name="username" required>
            </div>
            <div class="form-group">
                <label>Message:</label><br>
                <textarea name="content" required></textarea>
            </div>
            <button type="submit">Post</button>
        </form>
        <!-- Hidden input to handle JSON request body requirement of the API via HTML form -->
        <script>
            document.getElementById('postForm').onsubmit = async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                const data = Object.fromEntries(formData.entries());
                const response = await fetch('/messages', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                if (response.ok) { window.location.reload(); } else { alert('Error posting message'); }
            };
        </script>
    </div>

    <div class="controls">
        <form action="/messages" method="GET">
            Sort: 
            <select name="sort">
                <option value="DESC" {% if request.args.get('sort') == 'DESC' %}selected{% endif %}>Newest First</option>
                <option value="ASC" {% if request.args.get('sort') == 'ASC' %}selected{% endif %}>Oldest First</option>
            </select>
            Limit: <input type="number" name="limit" value="{{ limit }}" style="width: 60px;">
            Offset: <input type="number" name="offset" value="{{ offset }}" style="width: 60px;">
            <button type="submit">Filter</button>
        </form>
    </div>

    <div class="messages-list">
        {% for msg in messages %}
            <div class="message">
                <div class="username">{{ msg.username }}</div>
                <div class="content">{{ msg.content }}</div>
            </div>
        {% else %}
            <p>No messages found.</p>
        {% endfor %}
    </div>
</body>
</html>
"""

@app.route('/messages', methods=['GET'])
def get_messages():
    limit = request.args.get('limit', 10, type=int)
    offset = request.args.get('offset', 0, type=int)
    sort = request.args.get('sort', 'DESC').upper()
    
    if sort not in ['ASC', 'DESC']:
        sort = 'DESC'

    conn = get_db_connection()
    # Use parameterized query to prevent SQL injection
    query = f"SELECT username, content FROM messages ORDER BY timestamp {sort} LIMIT ? OFFSET ?"
    messages = conn.execute(query, (limit, offset)).fetchall()
    conn.close()

    return render_template_string(
        HTML_TEMPLATE, 
        messages=messages, 
        limit=limit, 
        offset=offset
    )

@app.route('/messages', methods=['POST'])
def post_message():
    data = request.get_json()
    if not data or 'username' not in data or 'content' not in data:
        return jsonify({"error": "Invalid input"}), 400

    username = data['username']
    content = data['content']

    # Basic validation
    if not username or not content:
        return jsonify({"error": "Username and content are required"}), 400

    try:
        conn = get_db_connection()
        conn.execute("INSERT INTO messages (username, content) VALUES (?, ?)", (username, content))
        conn.commit()
        conn.close()
        return jsonify({"status": "Successful operation"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)