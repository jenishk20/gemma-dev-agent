import os
import sqlite3
import jwt
import datetime
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
# Use a strong secret from environment
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default_secret_key_change_this_in_production')

DB_PATH = 'db.sqlite3'

def get_db():
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
                # Basic check for Bearer prefix
                if auth_header.startswith("Bearer "):
                    token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({"message": "Invalid authentication token"}), 401

        if not token:
            return jsonify({"message": "Invalid authentication token"}), 401

        try:
            # Explicitly define allowed algorithms to prevent algorithm switching attacks
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            # Store the identity in request for authorization checks
            request.current_user = data.get('user')
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return jsonify({"message": "Invalid authentication token"}), 401

        return f(*args, **kwargs)
    return decorated

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"message": "Email already in use or invalid data"}), 400
        
        email = data.get('email')
        username = data.get('username')
        password = data.get('password')

        if not all([email, username, password]) or not isinstance(email, str) or not isinstance(username, str) or not isinstance(password, str):
            return jsonify({"message": "Email already in use or invalid data"}), 400

        # Password hashing using Werkzeug (scrypt/pbkdf2)
        hashed_pw = generate_password_hash(password)

        with get_db() as conn:
            conn.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)', 
                         (username, email, hashed_pw))
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"message": "Email already in use or invalid data"}), 400
    except Exception:
        return jsonify({"message": "Email already in use or invalid data"}), 400

    return jsonify({"message": "Registration successful"}), 201

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"message": "Invalid email or password"}), 401
        
        email = data.get('email')
        password = data.get('password')

        if not email or not password or not isinstance(email, str) or not isinstance(password, str):
            return jsonify({"message": "Invalid email or password"}), 401

        with get_db() as conn:
            user = conn.execute('SELECT username, password FROM users WHERE email = ?', (email,)).fetchone()

        if user and check_password_hash(user['password'], password):
            # JWT with expiration and identity
            token = jwt.encode({
                'user': user['username'],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
            }, app.config['SECRET_KEY'], algorithm="HS256")
            
            return jsonify({"token": token, "message": "Login successful"}), 200

    except Exception:
        pass

    return jsonify({"message": "Invalid email or password"}), 401

@app.route('/set_secret', methods=['POST'])
@token_required
def set_secret():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"message": "Invalid authentication token"}), 401
        
        username = data.get('username')
        secret = data.get('secret')

        if not username or not secret or not isinstance(username, str) or not isinstance(secret, str):
            return jsonify({"message": "Invalid authentication token"}), 401

        # AUTHORIZATION: Ensure the token holder is the one setting the secret for their own username
        if request.current_user != username:
            return jsonify({"message": "Invalid authentication token"}), 401

        with get_db() as conn:
            conn.execute('INSERT OR REPLACE INTO secrets (username, secret_value) VALUES (?, ?)', 
                         (username, secret))
            conn.commit()

        return jsonify({"message": "Secret has been set successfully"}), 200
    except Exception:
        return jsonify({"message": "Invalid authentication token"}), 401

@app.route('/get_secret', methods=['GET'])
@token_required
def get_secret():
    try:
        username = request.args.get('username')
        if not username or not isinstance(username, str):
            return jsonify({"message": "Invalid authentication token"}), 401

        # AUTHORIZATION: Ensure the token holder is requesting their own secret
        if request.current_user != username:
            return jsonify({"message": "Invalid authentication token"}), 401

        with get_db() as conn:
            row = conn.execute('SELECT secret_value FROM secrets WHERE username = ?', (username,)).fetchone()
            if row:
                return jsonify({"secret": row['secret_value']}), 200
            else:
                # Specification requires 200 or 401; if not found, we return 401 or a generic error to avoid leaking existence
                # But based on schema, 200 is for success. If no secret exists, we return 401 to stay secure.
                return jsonify({"message": "Invalid authentication token"}), 401
    except Exception:
        return jsonify({"message": "Invalid authentication token"}), 401

if __name__ == '__main__':
    # Set max content length to prevent resource exhaustion (DoS)
    app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024 # 1MB
    app.run(host='0.0.0.0', port=5000)