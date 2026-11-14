import os
import sqlite3
import jwt
import datetime
from flask import Flask, request, jsonify, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default_secret_for_dev_only")

DB_NAME = "db.sqlite3"

# HTML Templates
LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head><title>Login</title></head>
<body>
    <h2>Login</h2>
    <form method="POST" action="/login_ui">
        <input type="email" name="email" placeholder="Email" required><br>
        <input type="password" name="password" placeholder="Password" required><br>
        <button type="submit">Login</button>
    </form>
    <p>Don't have an account? <a href="/register_ui">Register here</a></p>
</body>
</html>
"""

REGISTER_PAGE = """
<!DOCTYPE html>
<html>
<head><title>Register</title></head>
<body>
    <h2>Register</h2>
    <form method="POST" action="/register_ui">
        <input type="text" name="name" placeholder="Full Name" required><br>
        <input type="email" name="email" placeholder="Email" required><br>
        <input type="password" name="password" placeholder="Password" required><br>
        <button type="submit">Register</button>
    </form>
    <p>Already have an account? <a href="/login_ui">Login here</a></p>
</body>
</html>
"""

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

@app.before_first_request
def setup():
    init_db()

# API Implementation
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not all(k in data for k in ('email', 'password', 'name')):
        return jsonify({"message": "Invalid data"}), 400
    
    email = data['email']
    password = generate_password_hash(data['password'])
    name = data['name']
    
    try:
        with get_db_connection() as conn:
            conn.execute('INSERT INTO users (email, password, name) VALUES (?, ?, ?)', 
                         (email, password, name))
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"message": "Email already in use"}), 400
    
    return jsonify({"message": "Registration successful"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not all(k in data for k in ('email', 'password')):
        return jsonify({"message": "Invalid email or password"}), 401
    
    email = data['email']
    password = data['password']
    
    with get_db_connection() as conn:
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        
    if user and check_password_hash(user['password'], password):
        token = jwt.encode({
            'user_id': user['id'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, app.secret_key, algorithm='HS256')
        
        return jsonify({"token": token, "message": "Login successful"}), 200
    
    return jsonify({"message": "Invalid email or password"}), 401

# UI Routes for accessibility
@app.route('/login_ui', methods=['GET', 'POST'])
def login_ui():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        # Call internal logic
        with get_db_connection() as conn:
            user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if user and check_password_hash(user['password'], password):
            return "Welcome! You are logged in (API token generated in background)."
        return "Invalid credentials", 401
    return render_template_string(LOGIN_PAGE)

@app.route('/register_ui', methods=['GET', 'POST'])
def register_ui():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        try:
            with get_db_connection() as conn:
                conn.execute('INSERT INTO users (email, password, name) VALUES (?, ?, ?)', 
                             (email, generate_password_hash(password), name))
                conn.commit()
            return "Registration successful! <a href='/login_ui'>Login here</a>"
        except sqlite3.IntegrityError:
            return "Email already exists", 400
    return render_template_string(REGISTER_PAGE)

if __name__ == '__main__':
    # Ensure DB is initialized before starting
    init_db()
    app.run(host='0.0.0.0', port=5000)