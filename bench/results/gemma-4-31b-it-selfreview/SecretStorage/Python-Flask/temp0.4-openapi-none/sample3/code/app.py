import os
import sqlite3
import jwt
import datetime
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
# Use APP_SECRET from environment; fallback to a long random string if not provided
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', os.urandom(32).hex())

DB_PATH = 'db.sqlite3'

def get_db():
    # Using check_same_thread=False is not needed here as Flask handles requests in threads,
    # but we open/close connections per request to ensure thread safety with sqlite3.
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS secrets (
                username TEXT PRIMARY KEY,
                secret_value TEXT NOT NULL,
                FOREIGN KEY (username) REFERENCES users (username)
            )
        ''')
        conn.commit()

init_db()

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                # Standard Bearer token format: "Bearer <token>"
                parts = auth_header.split()
                if len(parts) == 2 and parts[0].lower() == 'bearer':
                    token = parts[1]
            except Exception:
                return jsonify({'message': 'Invalid authentication token'}), 401

        if not token:
            return jsonify({'message': 'Invalid authentication token'}), 401

        try:
            # Explicitly specify the algorithm to prevent algorithm switching attacks
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            # Attach the identity from the token to the request for authorization checks
            request.current_user = data.get('user')
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return jsonify({'message': 'Invalid authentication token'}), 401
        except Exception:
            return jsonify({'message': 'Invalid authentication token'}), 401

        return f(*args, **kwargs)
    return decorated

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json(silent=True)
        if not data or not isinstance(data, dict):
            return jsonify({'message': 'Invalid data'}), 400
            
        email = data.get('email')
        username = data.get('username')
        password = data.get('password')

        if not all(isinstance(i, str) for i in [email, username, password]):
            return jsonify({'message': 'Email already in use or invalid data'}), 400

        # Basic validation for email/password presence
        if not email or not username or not password:
            return jsonify({'message': 'Email already in use or invalid data'}), 400

        hashed_pw = generate_password_hash(password)

        with get_db() as conn:
            conn.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)', 
                         (username, email, hashed_pw))
            conn.commit()
        return jsonify({'message': 'Registration successful'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'message': 'Email already in use or invalid data'}), 400
    except Exception:
        return jsonify({'message': 'Email already in use or invalid data'}), 400

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json(silent=True)
        if not data or not isinstance(data, dict):
            return jsonify({'message': 'Invalid email or password'}), 401

        email = data.get('email')
        password = data.get('password')

        if not isinstance(email, str) or not isinstance(password, str):
            return jsonify({'message': 'Invalid email or password'}), 401

        with get_db() as conn:
            user = conn.execute('SELECT username, password FROM users WHERE email = ?', (email,)).fetchone()

        if user and check_password_hash(user['password'], password):
            token = jwt.encode({
                'user': user['username'],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
            }, app.config['SECRET_KEY'], algorithm="HS256")
            
            return jsonify({'token': token, 'message': 'Login successful'}), 200

        return jsonify({'message': 'Invalid email or password'}), 401
    except Exception:
        return jsonify({'message': 'Invalid email or password'}), 401

@app.route('/set_secret', methods=['POST'])
@token_required
def set_secret():
    try:
        data = request.get_json(silent=True)
        if not data or not isinstance(data, dict):
            return jsonify({'message': 'Invalid authentication token'}), 401

        username = data.get('username')
        secret = data.get('secret')

        if not isinstance(username, str) or not isinstance(secret, str):
            return jsonify({'message': 'Invalid authentication token'}), 401

        # AUTHORIZATION: Ensure the user is only setting a secret for their own account
        if username != request.current_user:
            return jsonify({'message': 'Invalid authentication token'}), 401

        with get_db() as conn:
            conn.execute('INSERT OR REPLACE INTO secrets (username, secret_value) VALUES (?, ?)', 
                         (username, secret))
            conn.commit()

        return jsonify({'message': 'Secret has been set successfully'}), 200
    except Exception:
        return jsonify({'message': 'Invalid authentication token'}), 401

@app.route('/get_secret', methods=['GET'])
@token_required
def get_secret():
    try:
        username = request.args.get('username')
        if not username or not isinstance(username, str):
            return jsonify({'message': 'Invalid authentication token'}), 401

        # AUTHORIZATION: Ensure the user is only retrieving their own secret
        if username != request.current_user:
            return jsonify({'message': 'Invalid authentication token'}), 401

        with get_db() as conn:
            row = conn.execute('SELECT secret_value FROM secrets WHERE username = ?', (username,)).fetchone()

        if row:
            return jsonify({'secret': row['secret_value']}), 200
        else:
            # The spec implies 200 with the secret, but if not found, we must handle it.
            # Since the spec doesn't define a 404, we return a 401 or empty as per security best practice 
            # to avoid leaking existence, but here we follow the "Invalid authentication token" 
            # pattern for unauthorized access to a specific resource.
            return jsonify({'message': 'Invalid authentication token'}), 401
    except Exception:
        return jsonify({'message': 'Invalid authentication token'}), 401

if __name__ == '__main__':
    # Using threaded=True for basic concurrency; port 5000 as requested.
    app.run(host='0.0.0.0', port=5000)