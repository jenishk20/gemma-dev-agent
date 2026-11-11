import os
import sqlite3
import uuid
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default-secret-key-for-dev')

DB_NAME = 'db.sqlite3'

def get_db_connection():
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
                password_hash TEXT NOT NULL,
                email TEXT NOT NULL
            )
        ''')
        conn.commit()

@app.route('/invite_user', methods=['POST'])
def invite_user():
    data = request.get_json()
    if not data or 'email' not in data:
        return jsonify({"message": "Email is required"}), 400
    
    email = data['email']
    
    with get_db_connection() as conn:
        # Check if invitation already exists for this email
        row = conn.execute('SELECT invite_id FROM invitations WHERE email = ?', (email,)).fetchone()
        if row:
            return jsonify({
                "invite_id": row['invite_id'],
                "message": "Invitation already exists for this email."
            }), 200
        
        # Create new invitation
        invite_id = str(uuid.uuid4())
        conn.execute('INSERT INTO invitations (invite_id, email) VALUES (?, ?)', (invite_id, email))
        conn.commit()
        
        return jsonify({
            "invite_id": invite_id,
            "message": "Invitation created successfully."
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
        return jsonify({"message": "Missing required fields: invite_id, user_name, password"}), 400

    with get_db_connection() as conn:
        # Validate invitation
        invitation = conn.execute('SELECT email FROM invitations WHERE invite_id = ? AND used = 0', (invite_id,)).fetchone()
        if not invitation:
            return jsonify({"message": "Invalid invite_id"}), 401
        
        # Check if username already exists
        existing_user = conn.execute('SELECT id FROM users WHERE username = ?', (user_name,)).fetchone()
        if existing_user:
            return jsonify({"message": "Username already exists. Try providing different username."}), 400
        
        # Hash password and create user
        pwd_hash = generate_password_hash(password)
        email = invitation['email']
        
        try:
            conn.execute('INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)', 
                        (user_name, pwd_hash, email))
            # Mark invitation as used
            conn.execute('UPDATE invitations SET used = 1 WHERE invite_id = ?', (invite_id,))
            conn.commit()
        except sqlite3.IntegrityError:
            return jsonify({"message": "Username already exists."}), 400

    return jsonify({"message": "User created successfully"}), 200

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)