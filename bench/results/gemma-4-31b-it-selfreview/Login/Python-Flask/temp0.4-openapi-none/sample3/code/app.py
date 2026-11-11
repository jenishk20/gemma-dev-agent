import os
import sqlite3
import jwt
import datetime
from flask import Flask, request, jsonify, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
# Ensure a strong secret key is used from environment
app.secret_key = os.environ.get("APP_SECRET", "fallback_secure_random_string_for_dev_only")

DB_NAME = "db.sqlite3"

def get_db_connection():
    # Use check_same_thread=False if using multi-threading, 
    # but for this simple app, standard connection is fine.
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

# HTML Template for the frontend
# Using render_template_string with a static string is safe here as we don't pass 
# user input into the template string itself, but rather use it as a base.
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Login & Register</title>
    <style>
        body { font-family: sans-serif; display: flex; justify-content: center; margin-top: 50px; background: #f4f4f9; }
        .container { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 300px; }
        h2 { text-align: center; color: #333; }
        input { width: 100%; padding: 10px; margin: 10px 0; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; }
        button { width: 100%; padding: 10px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background: #0056b3; }
        .toggle { text-align: center; margin-top: 15px; font-size: 0.9rem; }
        .toggle a { color: #007bff; text-decoration: none; }
        #message { text-align: center; margin-bottom: 10px; color: red; font-size: 0.9rem; word-wrap: break-word; }
    </style>
</head>
<body>
    <div class="container">
        <h2 id="form-title">Login</h2>
        <div id="message"></div>
        <form id="auth-form">
            <input type="text" id="name" placeholder="Full Name" style="display:none;">
            <input type="email" id="email" placeholder="Email" required>
            <input type="password" id="password" placeholder="Password" required>
            <button type="submit" id="submit-btn">Login</button>
        </form>
        <div class="toggle">
            <span id="toggle-text">Don't have an account?</span> 
            <a href="#" id="toggle-link">Register</a>
        </div>
    </div>

    <script>
        const form = document.getElementById('auth-form');
        const title = document.getElementById('form-title');
        const nameInput = document.getElementById('name');
        const submitBtn = document.getElementById('submit-btn');
        const toggleText = document.getElementById('toggle-text');
        const toggleLink = document.getElementById('toggle-link');
        const msgDiv = document.getElementById('message');

        let isLogin = true;

        toggleLink.onclick = (e) => {
            e.preventDefault();
            isLogin = !isLogin;
            title.innerText = isLogin ? 'Login' : 'Register';
            nameInput.style.display = isLogin ? 'none' : 'block';
            submitBtn.innerText = isLogin ? 'Login' : 'Register';
            toggleText.innerText = isLogin ? "Don't have an account?" : "Already have an account?";
            toggleLink.innerText = isLogin ? 'Register' : 'Login';
            msgDiv.innerText = '';
        };

        form.onsubmit = async (e) => {
            e.preventDefault();
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const name = document.getElementById('name').value;
            
            const endpoint = isLogin ? '/login' : '/register';
            const payload = isLogin ? { email, password } : { email, password, name };

            try {
                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                const data = await response.json();
                if (response.ok) {
                    msgDiv.style.color = 'green';
                    msgDiv.innerText = isLogin ? 'Login successful! Token: ' + data.token : 'Registration successful! Please login.';
                    if (!isLogin) {
                        setTimeout(() => toggleLink.click(), 2000);
                    }
                } else {
                    msgDiv.style.color = 'red';
                    msgDiv.innerText = data.message || 'An error occurred';
                }
            } catch (err) {
                msgDiv.style.color = 'red';
                msgDiv.innerText = 'Network error occurred';
            }
        };
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/register', methods=['POST'])
def register():
    # Resource Exhaustion: Limit request body size (Flask does this via MAX_CONTENT_LENGTH, 
    # but we check for JSON existence here).
    try:
        data = request.get_json(silent=True)
    except Exception:
        return jsonify({"message": "Invalid JSON"}), 400

    if data is None or not isinstance(data, dict):
        return jsonify({"message": "Invalid data"}), 400

    # Validate required fields and types
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')

    if not all(isinstance(v, str) for v in [email, password, name]) or not email or not password or not name:
        return jsonify({"message": "Email already in use or invalid data"}), 400
    
    # Password hashing: Werkzeug uses pbkdf2:sha256 with a salt by default (strong KDF)
    hashed_pw = generate_password_hash(password)
    
    try:
        with get_db_connection() as conn:
            # SQL Injection Prevention: Using parameterized queries
            conn.execute('INSERT INTO users (email, password, name) VALUES (?, ?, ?)', (email, hashed_pw, name))
            conn.commit()
    except sqlite3.IntegrityError:
        # Handle duplicate email as per OpenAPI spec
        return jsonify({"message": "Email already in use or invalid data"}), 400
    except Exception:
        # Error Handling: Generic error to avoid leaking internal details
        return jsonify({"message": "Internal server error"}), 400
    
    return jsonify({"message": "Registration successful"}), 201

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json(silent=True)
    except Exception:
        return jsonify({"message": "Invalid JSON"}), 401

    if data is None or not isinstance(data, dict):
        return jsonify({"message": "Invalid email or password"}), 401
    
    email = data.get('email')
    password = data.get('password')
    
    if not all(isinstance(v, str) for v in [email, password]) or not email or not password:
        return jsonify({"message": "Invalid email or password"}), 401
    
    try:
        with get_db_connection() as conn:
            # SQL Injection Prevention: Parameterized query
            user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
            
        # Constant-time comparison is handled by check_password_hash
        if user and check_password_hash(user['password'], password):
            # Secrets/Tokens: Use a strong secret, set expiry, and specify algorithm
            token = jwt.encode(
                {
                    'user_id': user['id'], 
                    'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24),
                    'iat': datetime.datetime.utcnow()
                },
                app.secret_key,
                algorithm="HS256"
            )
            return jsonify({"token": token, "message": "Login successful"}), 200
    except Exception:
        # Error Handling: Generic error to avoid leaking internal details
        return jsonify({"message": "Internal server error"}), 401
    
    return jsonify({"message": "Invalid email or password"}), 401

if __name__ == '__main__':
    # Limit request size to prevent resource exhaustion (e.g., 1MB)
    app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024
    app.run(host='0.0.0.0', port=5000)