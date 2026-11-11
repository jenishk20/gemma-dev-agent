import os
import asyncio
import sqlite3
import jwt
import datetime
from aiohttp import web
from passlib.hash import pbkdf2_sha256

# Configuration
APP_SECRET = os.environ.get("APP_SECRET", "default_secret_key_change_me")
DB_PATH = "db.sqlite3"

# Database Initialization
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    # Secrets table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS secrets (
            username TEXT PRIMARY KEY,
            secret_value TEXT NOT NULL,
            FOREIGN KEY(username) REFERENCES users(username)
        )
    ''')
    conn.commit()
    conn.close()

# Helper functions for DB access
def db_query(query, params=(), fetch=False):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(query, params)
    result = None
    if fetch:
        result = cursor.fetchone()
    conn.commit()
    conn.close()
    return result

# Middleware/Decorator for JWT Authentication
def authenticated(handler):
    async def wrapper(request):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return web.json_response({'message': 'Invalid authentication token'}, status=401)
        
        token = auth_header.split(' ')[1]
        try:
            payload = jwt.decode(token, APP_SECRET, algorithms=['HS256'])
            request['user_payload'] = payload
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return web.json_response({'message': 'Invalid authentication token'}, status=401)
        
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
            return web.json_response({'message': 'Invalid data'}, status=400)

        hashed_pw = pbkdf2_sha256.hash(password)
        db_query("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (username, email, hashed_pw))
        
        return web.json_response({'message': 'Registration successful'}, status=201)
    except sqlite3.IntegrityError:
        return web.json_response({'message': 'Email already in use or invalid data'}, status=400)
    except Exception:
        return web.json_response({'message': 'Bad Request'}, status=400)

async def login(request):
    try:
        data = await request.json()
        email = data.get('email')
        password = data.get('password')

        user = db_query("SELECT username, password FROM users WHERE email = ?", (email,), fetch=True)
        if user and pbkdf2_sha256.verify(password, user[1]):
            token = jwt.encode({
                'username': user[0],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
            }, APP_SECRET, algorithm='HS256')
            
            return web.json_response({'token': token, 'message': 'Login successful'}, status=200)
        
        return web.json_response({'message': 'Invalid email or password'}, status=401)
    except Exception:
        return web.json_response({'message': 'Invalid email or password'}, status=401)

@authenticated
async def set_secret(request):
    try:
        data = await request.json()
        username = data.get('username')
        secret = data.get('secret')
        
        # Verify that the token belongs to the username being modified
        if request['user_payload'].get('username') != username:
            return web.json_response({'message': 'Unauthorized access to this user secret'}, status=401)

        db_query("INSERT OR REPLACE INTO secrets (username, secret_value) VALUES (?, ?)", (username, secret))
        return web.json_response({'message': 'Secret has been set successfully'}, status=200)
    except Exception:
        return web.json_response({'message': 'Bad Request'}, status=400)

@authenticated
async def get_secret(request):
    username = request.query.get('username')
    if not username:
        return web.json_response({'message': 'Username query parameter is required'}, status=400)
    
    # Verify that the token belongs to the username being requested
    if request['user_payload'].get('username') != username:
        return web.json_response({'message': 'Invalid authentication token'}, status=401)

    result = db_query("SELECT secret_value FROM secrets WHERE username = ?", (username,), fetch=True)
    if result:
        return web.json_response({'secret': result[0]}, status=200)
    else:
        return web.json_response({'secret': None}, status=200)

# App Setup
app = web.Application()
app.add_routes([
    web.post('/register', register),
    web.post('/login', login),
    web.post('/set_secret', set_secret),
    web.get('/get_secret', get_secret),
])

if __name__ == '__main__':
    init_db()
    web.run_app(app, host='0.0.0.0', port=5000)