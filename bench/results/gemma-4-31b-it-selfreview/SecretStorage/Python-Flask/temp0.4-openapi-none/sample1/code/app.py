import os
import sqlite3
import jwt
import datetime
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
# Use the provided APP_SECRET env variable
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default_secret_key_for_dev_only')

DB_NAME = 'db.sqlite3'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
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
            try:
                # Expecting "Bearer <token>"
                parts = auth_header.split()
                if len(parts) == 2 and parts[0].lower() == 'bearer':
                    token = parts[1]
            except Exception:
                return jsonify({"message": "Invalid authentication token"}), 401

        if not token:
            return jsonify({"message": "Invalid authentication token"}), 401

        try:
            # Explicitly define the allowed algorithm to prevent algorithm switching attacks
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            # Store the identity in the request context for authorization checks
            request.user_identity = data.get('user')
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return jsonify({"message": "Invalid authentication token"}), 401
        except Exception:
            return jsonify({"message": "Invalid authentication token"}), 401

        return f(*args, **kwargs)
    return decorated

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json(silent=True)
        if not data or not all(k in data for k in ('email', 'username', 'password')):
            return jsonify({"message": "Email already in use or invalid data"}), 400

        email = str(data['email'])
        username = str(data['username'])
        password = str(data['password'])

        if not email or not username or not password:
            return jsonify({"message": "Email already in use or invalid data"}), 400

        # Werkzeug uses pbkdf2:sha256 with a salt by default
        hashed_pw = generate_password_hash(password)

        with get_db_connection() as conn:
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
        if not data or not all(k in data for k in ('email', 'password')):
            return jsonify({"message": "Invalid email or password"}), 401

        email = str(data['email'])
        password = str(data['password'])

        with get_db_connection() as conn:
            user = conn.execute('SELECT username, password FROM users WHERE email = ?', (email,)).fetchone()

        if user and check_password_hash(user['password'], password):
            # Set a reasonable expiration time
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
        if not data or not all(k in data for k in ('username', 'secret')):
            return jsonify({"message": "Invalid authentication token"}), 401 # Matching OpenAPI 401 for auth/validation errors in this context

        username = str(data['username'])
        secret = str(data['secret'])

        # AUTHORIZATION: Ensure the token identity matches the username being modified
        if request.user_identity != username:
            return jsonify({"message": "Invalid authentication token"}), 401

        with get_db_connection() as conn:
            # Verify user exists to maintain referential integrity
            user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
            if not user:
                return jsonify({"message": "Invalid authentication token"}), 401
            
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
        if not username:
            return jsonify({"message": "Invalid authentication token"}), 401

        # AUTHORIZATION: Ensure the token identity matches the username being requested
        if request.user_identity != username:
            return jsonify({"message": "Invalid authentication token"}), 401

        with get_db_connection() as conn:
            row = conn.execute('SELECT secret_value FROM secrets WHERE username = ?', (username,)).fetchone()
            if row:
                return jsonify({"secret": row['secret_value']}), 200
            else:
                # If no secret exists, we still return 200 or 404? 
                # OpenAPI says 200 for success, but doesn't specify "not found".
                # To be safe and follow the "Secret retrieved successfully" 200 response:
                return jsonify({"secret": ""}), 200
    except Exception:
        return jsonify({"message": "Invalid authentication token"}), 401

if __name__ == '__main__':
    # Use a production-ready server in real scenarios, but for this task:
    app.run(host='0.0.0.0', port=5000)