import os
import asyncio
import sqlite3
import jwt
import datetime
from aiohttp import web
from passlib.hash import pbkdf2_sha256

# Configuration
DB_NAME = "db.sqlite3"
APP_SECRET = os.environ.get("APP_SECRET", "default_secret_key_for_dev")

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

async def db_query(query, params=(), fetchone=False, commit=False):
    """Helper to run sqlite queries in a thread pool to avoid blocking the event loop."""
    def _execute():
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = None
        if fetchone:
            result = cursor.fetchone()
        elif not commit:
            result = cursor.fetchall()
        if commit:
            conn.commit()
        conn.close()
        return result
    return await asyncio.to_thread(_execute)

async def handle_register(request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"message": "Invalid JSON"}, status=400)

    email = data.get("email")
    password = data.get("password")
    name = data.get("name")

    if not email or not password or not name:
        return web.json_response({"message": "Email, password, and name are required"}, status=400)

    hashed_pw = pbkdf2_sha256.hash(password)
    
    try:
        await db_query(
            "INSERT INTO users (email, password, name) VALUES (?, ?, ?)",
            (email, hashed_pw, name),
            commit=True
        )
    except sqlite3.IntegrityError:
        return web.json_response({"message": "Email already in use or invalid data"}, status=400)
    except Exception as e:
        return web.json_response({"message": str(e)}, status=500)

    return web.json_response({"message": "Registration successful"}, status=201)

async def handle_login(request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"message": "Invalid JSON"}, status=400)

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return web.json_response({"message": "Email and password are required"}, status=400)

    user = await db_query("SELECT password FROM users WHERE email = ?", (email,), fetchone=True)

    if user and pbkdf2_sha256.verify(password, user[0]):
        # Generate JWT
        payload = {
            "email": email,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }
        token = jwt.encode(payload, APP_SECRET, algorithm="HS256")
        return web.json_response({
            "token": token,
            "message": "Login successful"
        }, status=200)

    return web.json_response({"message": "Invalid email or password"}, status=401)

async def init_app():
    app = web.Application()
    app.add_routes([
        web.post('/register', handle_register),
        web.post('/login', handle_login),
    ])
    return app

if __name__ == "__main__":
    init_db()
    app = asyncio.run(init_app()) # This is not quite right for aiohttp, usually we use web.run_app
    # Correct way to start aiohttp server
    web.run_app(app, host='0.0.0.0', port=5000)

# Since the prompt asks for a runnable file, let's fix the entry point logic
def run():
    init_db()
    app = web.Application()
    app.add_routes([
        web.post('/register', handle_register),
        web.post('/login', handle_login),
    ])
    web.run_app(app, host='0.0.0.0', port=5000)

if __name__ == "__main__":
    run()