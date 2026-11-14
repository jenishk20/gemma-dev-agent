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
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Invitations table: stores the invite_id and the email it was sent to
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invitations (
            invite_id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            used INTEGER DEFAULT 0
        )
    ''')
    # Users table: stores user credentials
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

async def run_query(query, params=(), fetchone=False, fetchall=False):
    """Helper to run sqlite queries in a thread pool to avoid blocking the event loop."""
    def _execute():
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            if fetchone:
                return cursor.fetchone()
            if fetchall:
                return cursor.fetchall()
            conn.commit()
            return None
    return await asyncio.to_thread(_execute)

async def handle_invite_user(request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"message": "Invalid JSON"}, status=400)

    email = data.get("email")
    if not email:
        return web.json_response({"message": "Email is required"}, status=400)

    # Check if an invitation already exists for this email
    existing = await run_query("SELECT invite_id FROM invitations WHERE email = ?", (email,), fetchone=True)
    
    if existing:
        invite_id = existing[0]
    else:
        invite_id = str(uuid.uuid4())
        await run_query("INSERT INTO invitations (invite_id, email) VALUES (?, ?)", (invite_id, email))

    return web.json_response({
        "invite_id": invite_id,
        "message": "Invitation created successfully"
    }, status=200)

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

    # Validate invitation
    invite = await run_query("SELECT email, used FROM invitations WHERE invite_id = ?", (invite_id,), fetchone=True)
    if not invite:
        return web.json_response({"message": "Invalid invite_id"}, status=401)
    
    email, used = invite
    if used:
        return web.json_response({"message": "Invitation has already been used"}, status=401)

    # Check if username already exists
    user_exists = await run_query("SELECT 1 FROM users WHERE username = ?", (user_name,), fetchone=True)
    if user_exists:
        return web.json_response({"message": "Username already exists. Try providing different username."}, status=400)

    # Hash password and create user
    pwd_hash = pbkdf2_sha256.hash(password)
    try:
        await run_query("INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)", (user_name, pwd_hash, email))
        # Mark invitation as used
        await run_query("UPDATE invitations SET used = 1 WHERE invite_id = ?", (invite_id,))
    except sqlite3.IntegrityError:
        return web.json_response({"message": "User with this email already exists"}, status=400)

    return web.json_response({"message": "User created"}, status=200)

async def init_app():
    app = web.Application()
    app.add_routes([
        web.post('/invite_user', handle_invite_user),
        web.post('/create_user', handle_create_user),
    ])
    return app

if __name__ == "__main__":
    init_db()
    app = asyncio.run(init_app()) # This is a simplified way to get the app object
    # Re-initialize app for the runner
    web.run_app(asyncio.run(init_app()), port=5000, address="0.0.0.0")

# Since the above logic in __main__ is slightly flawed for aiohttp's run_app, 
# let's use the standard pattern:
def main():
    init_db()
    app = web.Application()
    app.add_routes([
        web.post('/invite_user', handle_invite_user),
        web.post('/create_user', handle_create_user),
    ])
    web.run_app(app, port=5000, address="0.0.0.0")

if __name__ == "__main__":
    main()