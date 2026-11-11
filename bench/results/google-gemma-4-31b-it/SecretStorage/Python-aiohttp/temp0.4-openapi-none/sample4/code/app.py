import os
import asyncio
import sqlite3
import jwt
import datetime
from aiohttp import web
from passlib.hash import pbkdf2_sha256

# Configuration
DB_NAME = "db.sqlite3"
APP_SECRET = os.environ.get("APP_SECRET", "default_secret_key_change_me")
ALGORITHM = "HS256"

# Database initialization
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS secrets (
                username TEXT PRIMARY KEY,
                secret_value TEXT NOT NULL,
                FOREIGN KEY(username) REFERENCES users(username)
            )
        ''')
        conn.commit()

# Helper functions for DB access
def db_query(query, params=(), fetch=False, commit=False):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if commit:
            conn.commit()
        if fetch:
            return cursor.fetchall()
        return None

# Auth helpers
def create_token(username):
    payload = {
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24),
        "iat": datetime.datetime.utcnow(),
        "sub": username
    }
    return jwt.encode(payload, APP_SECRET, algorithm=ALGORITHM)

def verify_token(token):
    try:
        payload = jwt.decode(token, APP_SECRET, algorithms=[ALGORITHM])
        return payload["sub"]
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

# Middleware/Decorator for authentication
def auth_required(handler):
    async def wrapper(request):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return web.json_response({"message": "Invalid authentication token"}, status=401)
        
        token = auth_header.split(" ")[1]
        username = verify_token(token)
        if not username:
            return web.json_response({"message": "Invalid authentication token"}, status=401)
        
        request['auth_user'] = username
        return await handler(request)
    return wrapper

# Route Handlers
async def register(request):
    try:
        data = await request.json()
        email = data.get('email')
        username = data.get('username')
        password = data.get('password')

        if not email or not username or not password:
            return web.json_response({"message": "Missing required fields"}, status=400)

        hashed_pw = pbkdf2_sha256.hash(password)
        db_query("INSERT INTO users (email, username, password) VALUES (?, ?, ?)", 
                (email, username, hashed_pw), commit=True)
        
        return web.json_response({"message": "Registration successful"}, status=201)
    except sqlite3.IntegrityError:
        return web.json_response({"message": "Email already in use or invalid data"}, status=400)
    except Exception as e:
        return web.json_response({"message": str(e)}, status=400)

async def login(request):
    try:
        data = await request.json()
        email = data.get('email')
        password = data.get('password')

        user = db_query("SELECT username, password FROM users WHERE email = ?", (email,), fetch=True)
        if user and pbkdf2_sha256.verify(password, user[0][1]):
            token = create_token(user[0][0])
            return web.json_response({"token": token, "message": "Login successful"}, status=200)
        
        return web.json_response({"message": "Invalid email or password"}, status=401)
    except Exception:
        return web.json_response({"message": "Invalid request"}, status=400)

@auth_required
async def set_secret(request):
    try:
        data = await request.json()
        username = data.get('username')
        secret = data.get('secret')

        if not username or secret is None:
            return web.json_response({"message": "Missing username or secret"}, status=400)

        # Ensure the token matches the username being set for
        if request['auth_user'] != username:
            return web.json_response({"message": "Unauthorized access to this username"}, status=401)

        db_query("INSERT OR REPLACE INTO secrets (username, secret_value) VALUES (?, ?)", 
                (username, secret), commit=True)
        
        return web.json_response({"message": "Secret has been set successfully"}, status=200)
    except Exception:
        return web.json_response({"message": "Invalid request"}, status=400)

@auth_required
async def get_secret(request):
    username = request.query.get('username')
    if not username:
        return web.json_response({"message": "Username query parameter required"}, status=400)

    if request['auth_user'] != username:
        return web.json_response({"message": "Invalid authentication token"}, status=401)

    result = db_query("SELECT secret_value FROM secrets WHERE username = ?", (username,), fetch=True)
    if result:
        return web.json_response({"secret": result[0][0]}, status=200)
    else:
        return web.json_response({"secret": None}, status=200)

# App Setup
app = web.Application()
app.add_routes([
    web.post('/register', register),
    web.post('/login', login),
    web.post('/set_secret', set_secret),
    web.get('/get_secret', get_secret),
])

if __name__ == "__main__":
    init_db()
    web.run_app(app, host='0.0.0.0', port=5000)