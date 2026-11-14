import os
import sqlite3
import jwt
import datetime
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
# Ensure a strong secret is used from environment
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default_fallback_secret_key_for_dev_only')

DB_PATH = 'db.sqlite3'

def get_db_connection():
    # Using a connection per request to avoid threading issues with sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
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
            if auth_header.startswith('Bearer '):
                token = auth_header.split(" ")[1]
        
        if not token:
            return jsonify({'message': 'Invalid authentication token'}), 401
        
        try:
            # Explicitly specifying algorithms to prevent algorithm confusion attacks
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            request.current_user = data
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, Exception):
            return jsonify({'message': 'Invalid authentication token'}), 401
            
        return f(*args, **kwargs)
    return decorated

@app.route('/register', methods=['POST'])
def register():
    try:
        # Bound request size implicitly by Flask, but we check JSON validity
        data = request.get_json(silent=True)
        if not data or not all(k in data for k in ('email', 'username', 'password')):
            return jsonify({'message': 'Email already in use or invalid data'}), 400
        
        email = str(data['email'])
        username = str(data['username'])
        password = str(data['password'])
        
        if not email or not username or not password:
            return jsonify({'message': 'Email already in use or invalid data'}), 400

        # Werkzeug uses pbkdf2:sha256 with a salt by default, which is a strong KDF
        hashed_pw = generate_password_hash(password)
        
        with get_db_connection() as conn:
            # Parameterized query prevents SQL injection
            conn.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)', 
                         (username, email, hashed_pw))
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({'message': 'Email already in use or invalid data'}), 400
    except Exception:
        return jsonify({'message': 'Email already in use or invalid data'}), 400
    
    return jsonify({'message': 'Registration successful'}), 201

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json(silent=True)
        if not data or not all(k in data for k in ('email', 'password')):
            return jsonify({'message': 'Invalid email or password'}), 401
        
        email = str(data['email'])
        password = str(data['password'])
        
        with get_db_connection() as conn:
            # Parameterized query
            user = conn.execute('SELECT username, password FROM users WHERE email = ?', (email,)).fetchone()
            
        # check_password_hash uses constant-time comparison
        if user and check_password_hash(user['password'], password):
            token = jwt.encode({
                'username': user['username'],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
            }, app.config['SECRET_KEY'], algorithm="HS256")
            
            return jsonify({'token': token, 'message': 'Login successful'}), 200
    except Exception:
        pass
    
    return jsonify({'message': 'Invalid email or password'}), 401

@app.route('/set_secret', methods=['POST'])
@token_required
def set_secret():
    try:
        data = request.get_json(silent=True)
        if not data or not all(k in data for k in ('username', 'secret')):
            return jsonify({'message': 'Invalid data'}), 400
        
        username = str(data['username'])
        secret = str(data['secret'])
        
        # Authorization: Ensure the token's identity matches the resource owner
        if request.current_user.get('username') != username:
            return jsonify({'message': 'Invalid authentication token'}), 401
        
        with get_db_connection() as conn:
            # Parameterized query
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
        if not username:
            return jsonify({'message': 'Username is required'}), 400
        
        # Authorization: Ensure the token's identity matches the requested resource
        if request.current_user.get('username') != username:
            return jsonify({'message': 'Invalid authentication token'}), 401
        
        with get_db_connection() as conn:
            # Parameterized query
            row = conn.execute('SELECT secret_value FROM secrets WHERE username = ?', (username,)).fetchone()
            
        if row:
            return jsonify({'secret': row['secret_value']}), 200
        else:
            # Return 200 with empty/null secret as per common API patterns if not found, 
            # or as specified by the schema's example.
            return jsonify({'secret': None}), 200
    except Exception:
        return jsonify({'message': 'Invalid authentication token'}), 401

if __name__ == '__main__':
    # Port 5000, 0.0.0.0 as requested
    app.run(host='0.0.0.0', port=5000)