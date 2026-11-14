import os
import sqlite3
import jwt
import datetime
from flask import Flask, request, jsonify, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default-secret-key-change-me")

DB_NAME = "db.sqlite3"

# --- Database Setup ---
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

# --- Helper Functions ---
def create_token(email):
    payload = {
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24),
        'iat': datetime.datetime.utcnow(),
        'sub': email
    }
    return jwt.encode(payload, app.secret_key, algorithm='HS256')

# --- HTML Templates ---
# Since we must put everything in one file, we use render_template_string
LOGIN_PAGE = '''
<!DOCTYPE html>
<html>
<head><title>Login</title></head>
<body>
    <h2>Login</h2>
    <form method="POST" action="/login">
        Email: <input type="email" name="email" required><br>
        Password: <input type="password" name="password" required><br>
        <button type="submit">Login</button>
    </form>
    <p>Don't have an account? <a href="/register_page">Register here</a></p>
</body>
</html>
'''

REGISTER_PAGE = '''
<!DOCTYPE html>
<html>
<head><title>Register</title></head>
<body>
    <h2>Register</h2>
    <form method="POST" action="/register">
        Name: <input type="text" name="name" required><br>
        Email: <input type="email" name="email" required><br>
        Password: <input type="password" name="password" required><br>
        <button type="submit">Register</button>
    </form>
    <p>Already have an account? <a href="/login_page">Login here</a></p>
</body>
</html>
'''

# --- Routes ---

@app.route('/login_page')
def login_page():
    return render_template_string(LOGIN_PAGE)

@app.route('/register_page')
def register_page():
    return render_template_string(REGISTER_PAGE)

@app.route('/register', methods=['POST'])
def register():
    # Support both JSON (API) and Form data (Web UI)
    data = request.get_json() if request.is_json else request.form
    
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')

    if not email or not password or not name:
        return jsonify({"message": "Email, password, and name are required"}), 400

    hashed_pw = generate_password_hash(password)

    try:
        with get_db_connection() as conn:
            conn.execute('INSERT INTO users (email, password, name) VALUES (?, ?, ?)', 
                         (email, hashed_pw, name))
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"message": "Email already in use or invalid data"}), 400

    return jsonify({"message": "Registration successful"}), 201

@app.route('/login', methods=['POST'])
def login():
    # Support both JSON (API) and Form data (Web UI)
    data = request.get_json() if request.is_json else request.form
    
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    with get_db_connection() as conn:
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

    if user and check_password_hash(user['password'], password):
        token = create_token(email)
        return jsonify({
            "token": token,
            "message": "Login successful"
        }), 200
    
    return jsonify({"message": "Invalid email or password"}), 401

# --- Main ---
if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000, debug=False)