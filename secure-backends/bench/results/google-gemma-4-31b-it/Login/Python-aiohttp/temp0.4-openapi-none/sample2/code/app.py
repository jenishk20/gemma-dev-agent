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

# Database Setup
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

def get_db_conn():
    return sqlite3.connect(DB_NAME)

# Logic Helpers
def hash_password(password):
    return pbkdf2_sha256.hash(password)

def verify_password(password, hashed):
    return pbkdf2_sha256.verify(password, hashed)

def create_token(email):
    payload = {
        "email": email,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    return jwt.encode(payload, APP_SECRET, algorithm="HS256")

# Handlers
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

    hashed_pw = hash_password(password)
    
    conn = get_db_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (email, password, name) VALUES (?, ?, ?)", (email, hashed_pw, name))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return web.json_response({"message": "Email already in use"}, status=400)
    finally:
        conn.close()

    return web.json_response({"message": "Registration successful"}, status=201)

async def handle_login(request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"message": "Invalid JSON"}, status=400)

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return web.json_response({"message": "Email and password are required"}, status=401)

    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()

    if row and verify_password(password, row[0]):
        token = create_token(email)
        return web.json_response({
            "token": token,
            "message": "Login successful"
        }, status=200)

    return web.json_response({"message": "Invalid email or password"}, status=401)

# App Factory
async def init_app():
    init_db()
    app = web.Application()
    app.add_routes([
        web.post('/register', handle_register),
        web.post('/login', handle_login),
    ])
    return app

if __name__ == "__main__":
    app = asyncio.run(init_app()) if False else None # Placeholder for logic
    # Standard way to run aiohttp app
    async def run_server():
        app = await init_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 5000)
        await site.start()
        print("Server started at http://0.0.0.0:5000")
        while True:
            await asyncio.sleep(3600)

    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        pass