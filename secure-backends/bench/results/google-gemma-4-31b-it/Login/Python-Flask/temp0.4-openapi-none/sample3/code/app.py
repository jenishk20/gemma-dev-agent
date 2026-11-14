import os
import sqlite3
import jwt
import datetime
from flask import Flask, request, jsonify, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

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
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
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
        #message { text-align: center; margin-bottom: 10px; color: red; font-size: 0.9rem; }
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
    data = request.get_json()
    if not data or not all(k in data for k in ('email', 'password', 'name')):
        return jsonify({"message": "Invalid data"}), 400
    
    email, password, name = data['email'], data['password'], data['name']
    hashed_pw = generate_password_hash(password)
    
    try:
        with get_db_connection() as conn:
            conn.execute('INSERT INTO users (email, password, name) VALUES (?, ?, ?)', (email, hashed_pw, name))
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"message": "Email already in use"}), 400
    
    return jsonify({"message": "Registration successful"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not all(k in data for k in ('email', 'password')):
        return jsonify({"message": "Invalid data"}), 401
    
    email, password = data['email'], data['password']
    
    with get_db_connection() as conn:
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        
    if user and check_password_hash(user['password'], password):
        token = jwt.encode(
            {'user_id': user['id'], 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)},
            app.secret_key,
            algorithm="HS256"
        )
        return jsonify({"token": token, "message": "Login successful"}), 200
    
    return jsonify({"message": "Invalid email or password"}), 401

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)