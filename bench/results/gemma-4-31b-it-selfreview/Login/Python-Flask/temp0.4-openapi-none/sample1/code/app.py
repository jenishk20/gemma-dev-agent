import os
import sqlite3
import jwt
import datetime
from flask import Flask, request, jsonify, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
# Ensure a strong secret is used; fallback is only for local dev
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'dev_secret_key_do_not_use_in_prod')
DB_NAME = 'db.sqlite3'

# Database initialization
def get_db():
    # Use a context manager to ensure connections are closed
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
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

# HTML Templates - Using Jinja2's auto-escaping for content
BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Login App</title>
    <style>
        body { font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background-color: #f0f2f5; }
        .container { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 300px; }
        input { width: 100%; padding: 8px; margin: 10px 0; box-sizing: border-box; }
        button { width: 100%; padding: 10px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
        .link { text-align: center; margin-top: 15px; font-size: 0.9rem; }
    </style>
</head>
<body>
    <div class="container">
        {{ content | safe }}
    </div>
</body>
</html>
"""

LOGIN_PAGE = """
<h2 style="text-align:center">Login</h2>
<form method="POST" action="/login">
    <input type="email" name="email" placeholder="Email" required>
    <input type="password" name="password" placeholder="Password" required>
    <button type="submit">Login</button>
</form>
<div class="link">Don't have an account? <a href="/register">Register here</a></div>
"""

REGISTER_PAGE = """
<h2 style="text-align:center">Register</h2>
<form method="POST" action="/register">
    <input type="text" name="name" placeholder="Full Name" required>
    <input type="email" name="email" placeholder="Email" required>
    <input type="password" name="password" placeholder="Password" required>
    <button type="submit">Register</button>
</form>
<div class="link">Already have an account? <a href="/login">Login here</a></div>
"""

# Resource Exhaustion: Limit request size to 1MB
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template_string(BASE_TEMPLATE, content=REGISTER_PAGE)
    
    try:
        # Handle both JSON and Form data
        data = request.get_json() if request.is_json else request.form
        if data is None:
            return jsonify({"message": "Invalid request body"}), 400
            
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')

        if not all([email, password, name]):
            return jsonify({"message": "Email, password, and name are required"}), 400

        # Input validation: Basic email check to prevent absurdly long strings
        if len(email) > 255 or len(password) > 128 or len(name) > 255:
            return jsonify({"message": "Input too long"}), 400

        # Passwords are hashed using Werkzeug (pbkdf2:sha256 by default), which is a strong salted KDF
        hashed_pw = generate_password_hash(password)
        
        with get_db() as conn:
            # Parameterized query prevents SQL Injection
            conn.execute('INSERT INTO users (email, password, name) VALUES (?, ?, ?)', (email, hashed_pw, name))
            conn.commit()
            
    except sqlite3.IntegrityError:
        return jsonify({"message": "Email already in use or invalid data"}), 400
    except Exception:
        # Generic error to avoid leaking internal details
        return jsonify({"message": "An internal error occurred"}), 400

    return jsonify({"message": "Registration successful"}), 201

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template_string(BASE_TEMPLATE, content=LOGIN_PAGE)

    try:
        data = request.get_json() if request.is_json else request.form
        if data is None:
            return jsonify({"message": "Invalid request body"}), 400

        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({"message": "Email and password are required"}), 400

        with get_db() as conn:
            # Parameterized query prevents SQL Injection
            user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
            
        # check_password_hash uses constant-time comparison to prevent timing attacks
        if user and check_password_hash(user['password'], password):
            # JWT with explicit algorithm and expiration
            token = jwt.encode({
                'user_id': user['id'],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24),
                'iat': datetime.datetime.utcnow()
            }, app.config['SECRET_KEY'], algorithm='HS256')
            
            return jsonify({"token": token, "message": "Login successful"}), 200
        
        # Return 401 for both user not found and wrong password to prevent user enumeration
        return jsonify({"message": "Invalid email or password"}), 401
    except Exception:
        return jsonify({"message": "An internal error occurred"}), 401

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"message": "Token is missing"}), 401
        try:
            token = auth_header.split(" ")[1]
            # Explicitly verify algorithm to prevent algorithm switching attacks
            jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, IndexError):
            return jsonify({"message": "Token is invalid"}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/me', methods=['GET'])
@token_required
def me():
    return jsonify({"message": "Authenticated successfully"})

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)