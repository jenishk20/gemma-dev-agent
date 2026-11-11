import os
import sqlite3
import uuid
import json
from aiohttp import web
from passlib.hash import pbkdf2_sha256

# Configuration
DB_PATH = "db.sqlite3"
APP_SECRET = os.environ.get("APP_SECRET", "default_secret_key")

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
                password_hash TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL
            )
        ''')
        conn.commit()

async def invite_user(request):
    try:
        data = await request.json()
        email = data.get("email")
        if not email:
            return web.json_response({"message": "Email is required"}, status=400)

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # Check if invitation already exists
            cursor.execute("SELECT invite_id FROM invitations WHERE email = ?", (email,))
            row = cursor.fetchone()
            
            if row:
                invite_id = row[0]
            else:
                invite_id = str(uuid.uuid4())
                cursor.execute("INSERT INTO invitations (invite_id, email) VALUES (?, ?)", (invite_id, email))
                conn.commit()

        return web.json_response({
            "invite_id": invite_id,
            "message": f"Invitation sent to {email}"
        }, status=200)
    except Exception as e:
        return web.json_response({"message": str(e)}, status=400)

async def create_user(request):
    try:
        data = await request.json()
        invite_id = data.get("invite_id")
        user_name = data.get("user_name")
        password = data.get("password")

        if not all([invite_id, user_name, password]):
            return web.json_response({"message": "Missing required fields"}, status=400)

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Validate invitation
            cursor.execute("SELECT email FROM invitations WHERE invite_id = ? AND used = 0", (invite_id,))
            invite_row = cursor.fetchone()
            
            if not invite_row:
                return web.json_response({"message": "Invalid invite_id"}, status=401)
            
            email = invite_row[0]

            # Check if username already exists
            cursor.execute("SELECT 1 FROM users WHERE user_name = ?", (user_name,))
            if cursor.fetchone():
                return web.json_response({"message": "Username already exists. Try providing different username."}, status=400)

            # Hash password and create user
            password_hash = pbkdf2_sha256.hash(password)
            cursor.execute("INSERT INTO users (user_name, password_hash, email) VALUES (?, ?, ?)", 
                           (user_name, password_hash, email))
            
            # Mark invitation as used
            cursor.execute("UPDATE invitations SET used = 1 WHERE invite_id = ?", (invite_id,))
            conn.commit()

        return web.json_response({"message": "User created successfully"}, status=200)
    except Exception as e:
        return web.json_response({"message": str(e)}, status=400)

async def app_factory():
    app = web.Application()
    app.add_routes([
        web.post('/invite_user', invite_user),
        web.post('/create_user', create_user),
    ])
    return app

if __name__ == "__main__":
    init_db()
    app = None
    # We use a wrapper to handle the async factory in the runner
    async def start_server():
        global app
        app = await app_factory()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 5000)
        await site.start()
        print("Server started at http://0.0.0.0:5000")
        # Keep the loop running
        import asyncio
        await asyncio.Event().wait()

    import asyncio
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        pass