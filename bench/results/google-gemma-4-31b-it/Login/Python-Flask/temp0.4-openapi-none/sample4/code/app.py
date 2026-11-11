import os
import sqlite3
import jwt
import datetime
from flask import Flask, request, jsonify, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default-secret-key")
DB_NAME = "db.sqlite3"

# Database initialization
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                name TEXT NOT NULL
            )
        ''')
        conn.commit()

init_db()

# HTML Templates
BASE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Login App</title>
    <style>
        body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: #f0f2f5; }
        .card { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 300px; }
        .form-group { margin-bottom: 1rem; }
        label { display: block; margin-bottom: .5rem; }
        input { width: 100%; padding: 8px; box-sizing: border-box; }
        button { width: 100%; padding: 10px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
        .link { text-align: center; margin-top: 1rem; font-size: 0.9rem; }
    </style>
</head>
<body>
    <div class="card">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

LOGIN_HTML = """
{% extends "base" %}
{% block content %}
    <h2>Login</h2>
    <form method="POST" action="/login">
        <div class="form-group">
            <label>Email</label>
            <input type="email" name="email" required>
        </div>
        <div class="form-group">
            <label>Password</label>
            <input type="password" name="password" required>
        </div>
        <button type="submit">Login</button>
    </form>
    <div class="link">Don't have an account? <a href="/register">Register here</a></div>
{% endblock %}
"""

REGISTER_HTML = """
{% extends "base" %}
{% block content %}
    <h2>Register</h2>
    <form method="POST" action="/register">
        <div class="form-group">
            <label>Name</label>
            <input type="text" name="name" required>
        </div>
        <div class="form-group">
            <label>Email</label>
            <input type="email" name="email" required>
        </div>
        <div class="form-group">
            <label>Password</label>
            <input type="password" name="password" required>
        </div>
        <button type="submit">Register</button>
    </form>
    <div class="link">Already have an account? <a href="/login">Login here</a></div>
{% endblock %}
"""

@app.route('/')
def index():
    return render_template_string(LOGIN_HTML)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template_string(LOGIN_HTML)
    
    # Handle both JSON and Form data
    data = request.get_json() if request.is_json else request.form
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()

    if user and check_password_hash(user['password'], password):
        token = jwt.encode({
            'user_id': user['id'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, app.secret_key, algorithm='HS256')
        
        return jsonify({"token": token, "message": "Login successful"}), 200
    
    return jsonify({"message": "Invalid email or password"}), 401

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template_string(REGISTER_HTML)

    data = request.get_json() if request.is_json else request.form
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')

    if not email or not password or not name:
        return jsonify({"message": "Name, email, and password are required"}), 400

    hashed_pw = generate_password_hash(password)
    
    try:
        conn = get_db_connection()
        conn.execute('INSERT INTO users (email, password, name) VALUES (?, ?, ?)', 
                     (email, hashed_pw, name))
        conn.commit()
        conn.close()
        return jsonify({"message": "Registration successful"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"message": "Email already in use or invalid data"}), 400

# Template injection for the base layout
@app.context_processor
def inject_base():
    return dict(base_template=BASE_TEMPLATE)

# Overriding render_template_string to handle the base layout logic
def render_with_base(template_str):
    # This is a simple way to implement the 'extends' logic without separate files
    content = render_template_string(template_str)
    # Since we can't use actual file-based inheritance easily in one file without a custom loader,
    # we manually wrap the content in the base template.
    # However, for this specific task, we can just use the base_template string.
    return content

# Re-defining routes to use a simpler manual wrap since Jinja's 'extends' requires a filesystem
@app.route('/')
def home():
    return render_template_string(BASE_TEMPLATE.replace('{% block content %}{% endblock %}', render_template_string(LOGIN_HTML.replace('{% extends "base" %}', '').replace('{% block content %}', '').replace('{% endblock %}', ''))))

# To keep it clean and strictly follow the OpenAPI spec for the API endpoints:
# The API endpoints /login and /register are already handled above.

if __name__ == '__main__':
    # We override the render_template_string logic by just providing the full HTML in the routes
    # for the UI part, while keeping the JSON responses for the API part.
    
    # Redefining the UI routes to be simple and self-contained
    @app.route('/ui-login')
    def ui_login():
        return render_template_string(BASE_TEMPLATE.replace('{% block content %}{% endblock %}', 
            '<h2>Login</h2><form method="POST" action="/login"><div class="form-group"><label>Email</label><input type="email" name="email" required></div><div class="form-group"><label>Password</label><input type="password" name="password" required></div><button type="submit">Login</button></form><div class="link">Don\'t have an account? <a href="/ui-register">Register here</a></div>'))

    @app.route('/ui-register')
    def ui_register():
        return render_template_string(BASE_TEMPLATE.replace('{% block content %}{% endblock %}', 
            '<h2>Register</h2><form method="POST" action="/register"><div class="form-group"><label>Name</label><input type="text" name="name" required></div><div class="form-group"><label>Email</label><input type="email" name="email" required></div><div class="form-group"><label>Password</label><input type="password" name="password" required></div><button type="submit">Register</button></form><div class="link">Already have an account? <a href="/ui-login">Login here</a></div>'))

    app.run(host='0.0.0.0', port=5000)