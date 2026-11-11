import os
import sqlite3
import uuid
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash

app = Flask(__name__)
# Use the provided APP_SECRET env variable
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default_secret_key_for_dev')

DB_NAME = 'db.sqlite3'

def get_db_connection():
    # Using a context manager for the connection ensures it is closed properly
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        # Table for invitations
        conn.execute('''
            CREATE TABLE IF NOT EXISTS invitations (
                invite_id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                used INTEGER DEFAULT 0
            )
        ''')
        # Table for users
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT NOT NULL
            )
        ''')
        conn.commit()

@app.route('/invite_user', methods=['POST'])
def invite_user():
    # Resource exhaustion: Limit request body size (Flask does this via MAX_CONTENT_LENGTH, 
    # but we check for JSON existence here)
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"message": "Invalid JSON"}), 400
    
    email = data.get('email')
    if not email or not isinstance(email, str):
        return jsonify({"message": "Email is required and must be a string"}), 400
    
    # Basic email validation to prevent extremely long strings or injection attempts
    if len(email) > 320: # Maximum length of an email address per RFC 5321
        return jsonify({"message": "Email too long"}), 400

    conn = get_db_connection()
    try:
        # SQL Injection Prevention: Using parameterized queries (?)
        row = conn.execute('SELECT invite_id FROM invitations WHERE email = ?', (email,)).fetchone()
        if row:
            invite_id = row['invite_id']
        else:
            # Cryptographically secure randomness: uuid4 uses os.urandom
            invite_id = str(uuid.uuid4())
            conn.execute('INSERT INTO invitations (invite_id, email) VALUES (?, ?)', (invite_id, email))
            conn.commit()
        
        return jsonify({
            "invite_id": invite_id,
            "message": "Invitation created or retrieved successfully."
        }), 200
    except Exception:
        # Error handling: Catch exceptions and return generic error to avoid leaking internal details
        return jsonify({"message": "Internal server error"}), 500
    finally:
        conn.close()

@app.route('/create_user', methods=['POST'])
def create_user():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"message": "Invalid JSON"}), 400
    
    invite_id = data.get('invite_id')
    user_name = data.get('user_name')
    password = data.get('password')
    
    # Validate types and presence
    if not all(isinstance(x, str) for x in [invite_id, user_name, password]):
        return jsonify({"message": "invite_id, user_name, and password are required strings"}), 400

    # Resource exhaustion: limit input lengths
    if len(user_name) > 100 or len(password) > 128 or len(invite_id) > 100:
        return jsonify({"message": "Input length exceeds limit"}), 400

    conn = get_db_connection()
    try:
        # SQL Injection Prevention: Parameterized queries
        invitation = conn.execute('SELECT email FROM invitations WHERE invite_id = ? AND used = 0', (invite_id,)).fetchone()
        if not invitation:
            return jsonify({"message": "Invalid invite_id"}), 401
        
        email = invitation['email']
        
        # Check if username already exists
        existing_user = conn.execute('SELECT id FROM users WHERE username = ?', (user_name,)).fetchone()
        if existing_user:
            return jsonify({"message": "Username already exists. Try providing different username."}), 400
        
        # Secrets: generate_password_hash uses pbkdf2:sha256 with a salt by default (strong KDF)
        hashed_pw = generate_password_hash(password)
        
        conn.execute('INSERT INTO users (username, password, email) VALUES (?, ?, ?)', (user_name, hashed_pw, email))
        
        # Mark invitation as used to prevent reuse (Replay attack prevention)
        conn.execute('UPDATE invitations SET used = 1 WHERE invite_id = ?', (invite_id,))
        
        conn.commit()
        return jsonify({"message": "User created successfully"}), 200
        
    except Exception:
        # Error handling: Avoid leaking stack traces
        return jsonify({"message": "Internal server error"}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    init_db()
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)