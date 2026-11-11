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
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS secrets (
            username TEXT PRIMARY KEY,
            secret_value TEXT NOT NULL,
            FOREIGN KEY (username) REFERENCES users (username)
        )
    ''')
    conn.commit()
    conn.close()

def get_db_conn():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# Auth Helpers
def hash_password(password):
    return pbkdf2_sha256.hash(password)

def verify_password(password, hashed):
    return pbkdf2_sha256.verify(password, hashed)

def create_token(username):
    payload = {
        "username": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    return jwt.encode(payload, APP_SECRET, algorithm=ALGORITHM)

def verify_token(token):
    try:
        payload = jwt.decode(token, APP_SECRET, algorithms=[ALGORITHM])
        return payload["username"]
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

# Middleware for Bearer Auth
@web.middleware
async def auth_middleware(request, handler):
    # Public endpoints
    if request.path in ['/register', '/login']:
        return await handler(request)
    
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return web.json_response({'message': 'Invalid authentication token'}, status=401)
    
    token = auth_header.split(' ')[1]
    username = verify_token(token)
    if not username:
        return web.json_response({'message': 'Invalid authentication token'}, status=401)
    
    request['auth_user'] = username
    return await handler(request)

# Handlers
async def register(request):
    try:
        data = await request.json()
        email = data.get('email')
        username = data.get('username')
        password = data.get('password')

        if not all([email, username, password]):
            return web.json_response({'message': 'Invalid data'}, status=400)

        conn = get_db_conn()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)', 
                           (username, email, hash_password(password)))
            conn.commit()
        except sqlite3.IntegrityError:
            return web.json_response({'message': 'Email already in use or invalid data'}, status=400)
        finally:
            conn.close()

        return web.json_response({'message': 'Registration successful'}, status=201)
    except Exception:
        return web.json_response({'message': 'Bad Request'}, status=400)

async def login(request):
    try:
        data = await request.json()
        email = data.get('email')
        password = data.get('password')

        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT password FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        conn.close()

        if user and verify_password(password, user['password']):
            cursor = conn.cursor() # Re-open if needed, but we just need username
            # We need the username for the token
            conn = get_db_conn()
            cursor = conn.cursor()
            cursor.execute('SELECT username FROM users WHERE email = ?', (email,))
            username = cursor.fetchone()['username']
            conn.close()
            
            token = create_token(username)
            return web.json_response({'token': token, 'message': 'Login successful'}, status=200)
        
        return web.json_response({'message': 'Invalid email or password'}, status=401)
    except Exception:
        return web.json_response({'message': 'Invalid request'}, status=400)

async def set_secret(request):
    try:
        data = await request.json()
        username = data.get('username')
        secret = data.get('secret')
        
        # Verify that the token belongs to the username being set
        if request['auth_user'] != username:
            return web.json_response({'message': 'Invalid authentication token'}, status=401)

        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO secrets (username, secret_value) VALUES (?, ?)', (username, secret))
        conn.commit()
        conn.close()

        return web.json_response({'message': 'Secret has been set successfully'}, status=200)
    except Exception:
        return web.json_response({'message': 'Bad Request'}, status=400)

async def get_secret(request):
    username = request.query.get('username')
    if not username:
        return web.json_response({'message': 'Username is required'}, status=400)

    # Verify that the token belongs to the username requested
    if request['auth_user'] != username:
        return web.json_response({'message': 'Invalid authentication token'}, status=401)

    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT secret_value FROM secrets WHERE username = ?', (username,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return web.json_response({'secret': row['secret_value']}, status=200)
    else:
        return web.json_response({'secret': None}, status=200)

# App Setup
app = web.Application(middlewares=[auth_middleware])
app.add_routes([
    web.post('/register', register),
    web.post('/login', login),
    web.post('/set_secret', set_secret),
    web.get('/get_secret', get_secret),
])

if __name__ == '__main__':
    init_db()
    web.run_app(app, host='0.0.0.0', port=5000)