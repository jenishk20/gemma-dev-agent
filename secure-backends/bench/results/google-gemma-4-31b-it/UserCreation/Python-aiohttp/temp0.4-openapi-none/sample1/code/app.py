import os
import sqlite3
import uuid
import asyncio
from aiohttp import web
from passlib.hash import pbkdf2_sha256

# Configuration
DB_PATH = "db.sqlite3"
APP_SECRET = os.environ.get("APP_SECRET", "default_secret_key_for_dev")

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Table for invitations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invitations (
                invite_id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                used INTEGER DEFAULT 0
            )
        ''')
        # Table for users
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_name TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        ''')
        conn.commit()

async def get_db_connection():
    # Since sqlite3 is blocking, in a real high-load app we'd use aiosqlite.
    # For this implementation, we use the standard library sqlite3.
    return sqlite3.connect(DB_PATH)

async def handle_invite_user(request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"message": "Invalid JSON"}, status=400)

    email = data.get("email")
    if not email:
        return web.json_response({"message": "Email is required"}, status=400)

    conn = await get_db_connection()
    cursor = conn.cursor()
    
    # Check if invitation already exists for this email
    cursor.execute("SELECT invite_id FROM invitations WHERE email = ?", (email,))
    row = cursor.fetchone()
    
    if row:
        invite_id = row[0]
    else:
        invite_id = str(uuid.uuid4())
        cursor.execute("INSERT INTO invitations (invite_id, email) VALUES (?, ?)", (invite_id, email))
        conn.commit()
    
    conn.close()
    return web.json_response({
        "invite_id": invite_id,
        "message": f"Invitation sent to {email}"
    })

async def handle_create_user(request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"message": "Invalid JSON"}, status=400)

    invite_id = data.get("invite_id")
    user_name = data.get("user_name")
    password = data.get("password")

    if not all([invite_id, user_name, password]):
        return web.json_response({"message": "Missing required fields"}, status=400)

    conn = await get_db_connection()
    cursor = conn.cursor()

    # 1. Validate invite_id and get associated email
    cursor.execute("SELECT email FROM invitations WHERE invite_id = ? AND used = 0", (invite_id,))
    invite_row = cursor.fetchone()
    
    if not invite_row:
        conn.close()
        return web.json_response({"message": "Invalid invite_id"}, status=401)
    
    email = invite_row[0]

    # 2. Check if username already exists
    cursor.execute("SELECT 1 FROM users WHERE user_name = ?", (user_name,))
    if cursor.fetchone():
        conn.close()
        return web.json_response({"message": "Username already exists. Try providing different username."}, status=400)

    # 3. Create user and mark invitation as used
    password_hash = pbkdf2_sha256.hash(password)
    try:
        cursor.execute("INSERT INTO users (user_name, email, password_hash) VALUES (?, ?, ?)", 
                       (user_name, email, password_hash))
        cursor.execute("UPDATE invitations SET used = 1 WHERE invite_id = ?", (invite_id,))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return web.json_response({"message": "User with this email already exists"}, status=400)
    finally:
        conn.close()

    return web.json_response({"message": "User created successfully"}, status=200)

async def init_app():
    init_db()
    app = web.Application()
    app.router.add_post('/invite_user', handle_invite_user)
    app.router.add_post('/create_user', handle_create_user)
    return app

if __name__ == "__main__":
    web.run_app(init_app(), port=5000, address="0.0.0.0")