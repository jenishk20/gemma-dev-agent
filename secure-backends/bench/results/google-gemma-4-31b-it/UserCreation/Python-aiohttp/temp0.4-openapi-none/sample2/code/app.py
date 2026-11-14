import os
import uuid
import sqlite3
import asyncio
from aiohttp import web
from passlib.hash import pbkdf2_sha256

# Configuration
DB_NAME = "db.sqlite3"
APP_SECRET = os.environ.get("APP_SECRET", "default_secret_key_for_dev")

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Invitations table: stores email and the unique invite_id
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invitations (
            email TEXT PRIMARY KEY,
            invite_id TEXT UNIQUE NOT NULL
        )
    ''')
    # Users table: stores username, hashed password, and the invite_id used to join
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            invite_id TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

async def get_db_connection():
    # Using synchronous sqlite3 in a thread pool via run_in_executor 
    # is the standard way to handle sqlite with aiohttp since 
    # aiohttp is async and sqlite3 is sync.
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

async def handle_invite_user(request):
    try:
        data = await request.json()
        email = data.get("email")
        if not email:
            return web.json_response({"message": "Email is required"}, status=400)

        loop = asyncio.get_event_loop()
        def db_ops():
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT invite_id FROM invitations WHERE email = ?", (email,))
            row = cursor.fetchone()
            
            if row:
                invite_id = row[0]
            else:
                invite_id = str(uuid.uuid4())
                cursor.execute("INSERT INTO invitations (email, invite_id) VALUES (?, ?)", (email, invite_id))
                conn.commit()
            conn.close()
            return invite_id

        invite_id = await loop.run_in_executor(None, db_ops)
        return web.json_response({
            "invite_id": invite_id,
            "message": f"Invitation created for {email}"
        }, status=200)
    except Exception as e:
        return web.json_response({"message": str(e)}, status=400)

async def handle_create_user(request):
    try:
        data = await request.json()
        invite_id = data.get("invite_id")
        user_name = data.get("user_name")
        password = data.get("password")

        if not all([invite_id, user_name, password]):
            return web.json_response({"message": "Missing required fields"}, status=400)

        loop = asyncio.get_event_loop()
        
        def db_ops():
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            
            # 1. Validate invite_id exists and hasn't been used by another user
            cursor.execute("SELECT email FROM invitations WHERE invite_id = ?", (invite_id,))
            invite = cursor.fetchone()
            if not invite:
                conn.close()
                return "INVALID_INVITE", None

            # Check if this invite_id was already used to create a user
            cursor.execute("SELECT username FROM users WHERE invite_id = ?", (invite_id,))
            used = cursor.fetchone()
            if used:
                conn.close()
                return "INVALID_INVITE", None

            # 2. Check if username already exists
            cursor.execute("SELECT username FROM users WHERE username = ?", (user_name,))
            if cursor.fetchone():
                conn.close()
                return "USER_EXISTS", None

            # 3. Create user
            pw_hash = pbkdf2_sha256.hash(password)
            cursor.execute("INSERT INTO users (username, password_hash, invite_id) VALUES (?, ?, ?)", 
                           (user_name, pw_hash, invite_id))
            conn.commit()
            conn.close()
            return "SUCCESS", None

        result, _ = await loop.run_in_executor(None, db_ops)

        if result == "INVALID_INVITE":
            return web.json_response({"message": "Invalid invite_id"}, status=401)
        elif result == "USER_EXISTS":
            return web.json_response({"message": "Username already exists. Try providing different username."}, status=400)
        
        return web.json_response({"message": "User created successfully"}, status=200)
    except Exception as e:
        return web.json_response({"message": str(e)}, status=400)

async def init_app():
    app = web.Application()
    app.add_routes([
        web.post('/invite_user', handle_invite_user),
        web.post('/create_user', handle_create_user),
    ])
    return app

if __name__ == "__main__":
    init_db()
    app = asyncio.run(asyncio.run_coroutine_threadsafe(init_app(), asyncio.get_event_loop()) if False else None) 
    # The above is just a placeholder, use standard run_app
    from aiohttp import web
    app = web.Application()
    app.add_routes([
        web.post('/invite_user', handle_invite_user),
        web.post('/create_user', handle_create_user),
    ])
    web.run_app(app, host='0.0.0.0', port=5000)