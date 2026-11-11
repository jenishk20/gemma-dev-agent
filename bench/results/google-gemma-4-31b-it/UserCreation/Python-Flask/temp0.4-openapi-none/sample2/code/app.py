import os
import sqlite3
import uuid
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET', 'default_secret_key')

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
                user_name TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        conn.commit()

@app.route('/invite_user', methods=['POST'])
def invite_user():
    data = request.get_json()
    if not data or 'email' not in data:
        return jsonify({"message": "Email is required"}), 400
    
    email = data['email']
    
    try:
        with get_db_connection() as conn:
            # Check if invitation already exists for this email
            cursor = conn.execute('SELECT invite_id FROM invitations WHERE email = ?', (email,))
            row = cursor.fetchone()
            
            if row:
                invite_id = row['invite_id']
            else:
                # Create new invitation
                invite_id = str(uuid.uuid4())
                conn.execute('INSERT INTO invitations (invite_id, email) VALUES (?, ?)', (invite_id, email))
                conn.commit()
            
            return jsonify({
                "invite_id": invite_id,
                "message": "Invitation successfully retrieved or created."
            }), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500

@app.route('/create_user', methods=['POST'])
def create_user():
    data = request.get_json()
    if not data:
        return jsonify({"message": "Invalid request body"}), 400
    
    invite_id = data.get('invite_id')
    user_name = data.get('user_name')
    password = data.get('password')
    
    if not all([invite_id, user_name, password]):
        return jsonify({"message": "Missing required fields"}), 400

    try:
        with get_db_connection() as conn:
            # Validate invitation
            cursor = conn.execute('SELECT email FROM invitations WHERE invite_id = ? AND used = 0', (invite_id,))
            inv_row = cursor.fetchone()
            
            if not inv_row:
                return jsonify({"message": "Invalid invite_id"}), 401
            
            email = inv_row['email']
            
            # Check if username already exists
            cursor = conn.execute('SELECT 1 FROM users WHERE user_name = ?', (user_name,))
            if cursor.fetchone():
                return jsonify({"message": "Username already exists. Try providing different username."}), 400
            
            # Hash password and create user
            hashed_pw = generate_password_hash(password)
            conn.execute('INSERT INTO users (user_name, email, password) VALUES (?, ?, ?)', 
                         (user_name, email, hashed_pw))
            
            # Mark invitation as used
            conn.execute('UPDATE invitations SET used = 1 WHERE invite_id = ?', (invite_id,))
            conn.commit()
            
            return jsonify({"message": "User created successfully"}), 200
            
    except Exception as e:
        return jsonify({"message": str(e)}), 500

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)