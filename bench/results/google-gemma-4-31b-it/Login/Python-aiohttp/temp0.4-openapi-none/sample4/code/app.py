import os
import asyncio
import sqlite3
import jwt
import datetime
from aiohttp import web
from passlib.hash import pbkdf2_sha256

# Configuration
DB_NAME = "db.sqlite3"
SECRET_KEY = os.environ.get("APP_SECRET", "default_secret_key_for_dev")

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

async def get_db_connection():
    # Using a synchronous connection in a thread for sqlite3
    # In a production app, aiosqlite would be preferred
    return sqlite3.connect(DB_NAME)

async def handle_register(request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"message": "Invalid JSON"}, status=400)

    email = data.get("email")
    password = data.get("password")
    name = data.get("name")

    if not email or not password or not name:
        return web.json_response({"message": "Missing required fields"}, status=400)

    hashed_pw = pbkdf2_sha256.hash(password)

    conn = await get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (email, password, name) VALUES (?, ?, ?)", (email, hashed_pw, name))
        conn.commit()
    except sqlite3.IntegrityError:
        return web.json_response({"message": "Email already in use or invalid data"}, status=400)
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
        return web.json_response({"message": "Missing email or password"}, status=401)

    conn = await get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()

    if row and pbkdf2_sha256.verify(password, row[0]):
        payload = {
            "exp": datetime.datetime.utcnow() + datetime.timedelta(days=1),
            "iat": datetime.datetime.utcnow(),
            "sub": email
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
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
    app = asyncio.run(init_app())
    web.run_app(app, host='0.0.0.0', port=5000)