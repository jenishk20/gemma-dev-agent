import os
import sqlite3
import uuid
import json
from aiohttp import web
from passlib.hash import pbkdf2_sha256

# Configuration
DB_NAME = "db.sqlite3"
APP_SECRET = os.environ.get("APP_SECRET", "default_secret_key")

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Invitations table: stores email and a unique invite_id
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invitations (
            email TEXT PRIMARY KEY,
            invite_id TEXT UNIQUE NOT NULL,
            used INTEGER DEFAULT 0
        )
    ''')
    # Users table: stores username, hashed password, and the email associated with the invite
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            email TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

async def handle_invite_user(request):
    try:
        data = await request.json()
        email = data.get('email')
        if not email:
            return web.json_response({'message': 'Email is required'}, status=400)

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Check if invitation already exists for this email
        cursor.execute("SELECT invite_id FROM invitations WHERE email = ?", (email,))
        row = cursor.fetchone()
        
        if row:
            invite_id = row[0]
        else:
            invite_id = str(uuid.uuid4())
            cursor.execute("INSERT INTO invitations (email, invite_id) VALUES (?, ?)", (email, invite_id))
            conn.commit()
        
        conn.close()
        return web.json_response({
            'invite_id': invite_id,
            'message': 'Invitation created successfully'
        }, status=200)
    except Exception as e:
        return web.json_response({'message': str(e)}, status=500)

async def handle_create_user(request):
    try:
        data = await request.json()
        invite_id = data.get('invite_id')
        user_name = data.get('user_name')
        password = data.get('password')

        if not all([invite_id, user_name, password]):
            return web.json_response({'message': 'Missing required fields'}, status=400)

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # 1. Validate invitation
        cursor.execute("SELECT email FROM invitations WHERE invite_id = ? AND used = 0", (invite_id,))
        invite_row = cursor.fetchone()
        if not invite_row:
            conn.close()
            return web.json_response({'message': 'Invalid invite_id'}, status=401)
        
        email = invite_row[0]

        # 2. Check if username already exists
        cursor.execute("SELECT 1 FROM users WHERE username = ?", (user_name,))
        if cursor.fetchone():
            conn.close()
            return web.json_response({'message': 'Username already exists. Try providing different username.'}, status=400)

        # 3. Create user and mark invite as used
        password_hash = pbkdf2_sha256.hash(password)
        cursor.execute("INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)", 
                       (user_name, password_hash, email))
        cursor.execute("UPDATE invitations SET used = 1 WHERE invite_id = ?", (invite_id,))
        
        conn.commit()
        conn.close()
        
        return web.json_response({'message': 'User created successfully'}, status=200)
    except Exception as e:
        return web.json_response({'message': str(e)}, status=500)

async def init_app():
    app = web.Application()
    app.add_routes([
        web.post('/invite_user', handle_invite_user),
        web.post('/create_user', handle_create_user),
    ])
    return app

if __name__ == '__main__':
    init_db()
    app = init_app()
    web.run_app(app, host='0.0.0.0', port=5000)