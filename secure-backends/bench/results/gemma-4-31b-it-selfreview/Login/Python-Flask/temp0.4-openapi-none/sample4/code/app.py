import os
import sqlite3
import jwt
import datetime
from flask import Flask, request, jsonify, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import RequestEntityTooLarge

app = Flask(__name__)
# Use a strong secret from environment or a fallback for local dev
app.secret_key = os.environ.get("APP_SECRET", "dev-secret-fallback-key-12345")
DB_NAME = "db.sqlite3"

# Limit request size to prevent resource exhaustion (DoS)
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1MB limit

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

# HTML Templates (Static strings, no user input injected into templates)
BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
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
        {{ content | safe }}
    </div>
</body>
</html>
"""

LOGIN_CONTENT = """
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
    <div class="link">Don't have an account? <a href="/ui-register">Register here</a></div>
"""

REGISTER_CONTENT = """
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
    <div class="link">Already have an account? <a href="/ui-login">Login here</a></div>
"""

@app.errorhandler(RequestEntityTooLarge)
def handle_too_large(e):
    return jsonify({"message": "Request entity too large"}), 413

@app.errorhandler(Exception)
def handle_exception(e):
    # Prevent leaking stack traces/internal details
    return jsonify({"message": "An internal error occurred"}), 500

@app.route('/')
def index():
    return render_template_string(BASE_TEMPLATE, content=LOGIN_CONTENT)

@app.route('/ui-login')
def ui_login():
    return render_template_string(BASE_TEMPLATE, content=LOGIN_CONTENT)

@app.route('/ui-register')
def ui_register():
    return render_template_string(BASE_TEMPLATE, content=REGISTER_CONTENT)

@app.route('/login', methods=['POST'])
def login():
    # Ensure we only process JSON or Form data as per spec
    if request.is_json:
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"message": "Invalid JSON"}), 400
    else:
        data = request.form

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"message": "Invalid email or password"}), 401

    try:
        conn = get_db_connection()
        # Parameterized query to prevent SQL Injection
        user = conn.execute('SELECT id, password FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()

        # check_password_hash uses constant-time comparison to prevent timing attacks
        if user and check_password_hash(user['password'], password):
            # JWT with explicit algorithm and expiration
            token = jwt.encode({
                'user_id': user['id'],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
            }, app.secret_key, algorithm='HS256')
            
            return jsonify({"token": token, "message": "Login successful"}), 200
        
        return jsonify({"message": "Invalid email or password"}), 401
    except Exception:
        return handle_exception(None)

@app.route('/register', methods=['POST'])
def register():
    if request.is_json:
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"message": "Invalid JSON"}), 400
    else:
        data = request.form

    email = data.get('email')
    password = data.get('password')
    name = data.get('name')

    if not email or not password or not name:
        return jsonify({"message": "Email already in use or invalid data"}), 400

    # Password hashing using Werkzeug (scrypt/pbkdf2) which is a strong salted KDF
    hashed_pw = generate_password_hash(password)
    
    try:
        conn = get_db_connection()
        # Parameterized query to prevent SQL Injection
        conn.execute('INSERT INTO users (email, password, name) VALUES (?, ?, ?)', 
                     (email, hashed_pw, name))
        conn.commit()
        conn.close()
        return jsonify({"message": "Registration successful"}), 201
    except sqlite3.IntegrityError:
        # Email already exists (UNIQUE constraint)
        return jsonify({"message": "Email already in use or invalid data"}), 400
    except Exception:
        return handle_exception(None)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)