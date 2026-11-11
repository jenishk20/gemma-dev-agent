import os
import sqlite3
import uuid
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default_secret_key')

DB_PATH = 'db.sqlite3'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
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
                user_name TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        ''')
        conn.commit()

@app.route('/invite_user', methods=['POST'])
def invite_user():
    data = request.get_json()
    if not data or 'email' not in data:
        return jsonify({"message": "Email is required"}), 400
    
    email = data['email']
    
    db = get_db()
    # Check if invitation already exists for this email
    cursor = db.execute('SELECT invite_id FROM invitations WHERE email = ?', (email,))
    row = cursor.fetchone()
    
    if row:
        invite_id = row['invite_id']
    else:
        invite_id = str(uuid.uuid4())
        db.execute('INSERT INTO invitations (invite_id, email) VALUES (?, ?)', (invite_id, email))
        db.commit()
    
    return jsonify({
        "invite_id": invite_id,
        "message": "Invitation created or retrieved successfully"
    }), 200

@app.route('/create_user', methods=['POST'])
def create_user():
    data = request.get_json()
    if not data:
        return jsonify({"message": "Request body required"}), 400
    
    invite_id = data.get('invite_id')
    user_name = data.get('user_name')
    password = data.get('password')
    
    if not all([invite_id, user_name, password]):
        return jsonify({"message": "invite_id, user_name, and password are required"}), 400
    
    db = get_db()
    
    # Validate invitation
    cursor = db.execute('SELECT email FROM invitations WHERE invite_id = ? AND used = 0', (invite_id,))
    invite = cursor.fetchone()
    
    if not invite:
        return jsonify({"message": "Invalid invite_id"}), 401
    
    email = invite['email']
    
    # Check if username already exists
    cursor = db.execute('SELECT id FROM users WHERE user_name = ?', (user_name,))
    if cursor.fetchone():
        return jsonify({"message": "Username already exists. Try providing different username."}), 400

    # Hash password and create user
    pw_hash = generate_password_hash(password)
    try:
        db.execute('INSERT INTO users (user_name, email, password_hash) VALUES (?, ?, ?)', 
                   (user_name, email, pw_hash))
        # Mark invitation as used
        db.execute('UPDATE invitations SET used = 1 WHERE invite_id = ?', (invite_id,))
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"message": "Username or Email already exists"}), 400
    
    return jsonify({"message": "User created successfully"}), 200

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)