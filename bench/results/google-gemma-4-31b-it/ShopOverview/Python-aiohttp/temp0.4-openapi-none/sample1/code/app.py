import os
import sqlite3
import csv
import io
import jwt
from datetime import datetime, timedelta
from aiohttp import web
from passlib.hash import pbkdf2_sha256

# Configuration
DB_NAME = "db.sqlite3"
APP_SECRET = os.environ.get("APP_SECRET", "default_secret_key_for_dev")
COOKIE_NAME = "AUTH_COOKIE"

# Database Initialization
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS merchants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            merchant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            FOREIGN KEY (merchant_id) REFERENCES merchants(id)
        )
    ''')
    conn.commit()
    conn.close()

# Auth Helpers
def create_token(user_id):
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, APP_SECRET, algorithm="HS256")

def verify_token(token):
    try:
        payload = jwt.decode(token, APP_SECRET, algorithms=["HS256"])
        return payload["user_id"]
    except Exception:
        return None

# Middleware for Cookie Auth
@web.middleware
async def auth_middleware(request, handler):
    # Only protect specific routes
    if request.path == '/merchants/upload-wares' or request.path == '/wares':
        token = request.cookies.get(COOKIE_NAME)
        user_id = verify_token(token) if token else None
        if not user_id:
            return web.Response(text="Unauthorized", status=401)
        request['user_id'] = user_id
    return await handler(request)

# Handlers
async def register(request):
    try:
        data = await request.json()
        email = data.get('email')
        name = data.get('name')
        password = data.get('password')
        
        if not all([email, name, password]):
            return web.Response(text="Invalid input", status=400)
        
        hashed_pw = pbkdf2_sha256.hash(password)
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO merchants (email, name, password) VALUES (?, ?, ?)", 
                           (email, name, hashed_pw))
            conn.commit()
        except sqlite3.IntegrityError:
            return web.Response(text="Email already exists", status=400)
        finally:
            conn.close()
            
        return web.Response(status=201)
    except Exception:
        return web.Response(text="Invalid input", status=400)

async def login(request):
    try:
        data = await request.json()
        email = data.get('email')
        password = data.get('password')
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, password FROM merchants WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()
        
        if user and pbkdf2_sha256.verify(password, user[1]):
            token = create_token(user[0])
            resp = web.json_response("Login successful")
            resp.set_cookie(COOKIE_NAME, token, httponly=True)
            return resp
        
        return web.json_response({"error": "Invalid email or password"}, status=401)
    except Exception:
        return web.json_response({"error": "Invalid input"}, status=400)

async def upload_wares(request):
    try:
        data = await request.json()
        csv_text = data.get('csv', '')
        user_id = request['user_id']
        
        f = io.StringIO(csv_text)
        reader = csv.reader(f)
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        for row in reader:
            if len(row) != 3:
                conn.close()
                return web.Response(text="Invalid CSV format", status=400)
            
            name, desc, price = row
            cursor.execute("INSERT INTO wares (merchant_id, name, description, price) VALUES (?, ?, ?, ?)", 
                           (user_id, name, desc, float(price)))
        
        conn.commit()
        conn.close()
        return web.Response(status=200)
    except Exception:
        return web.Response(text="Invalid CSV format", status=400)

async def get_wares(request):
    min_price = request.query.get('minPrice', None)
    max_price = request.query.get('maxPrice', None)
    
    query = "SELECT w.name, w.price, w.description, m.email FROM wares w JOIN merchants m ON w.merchant_id = m.id WHERE 1=1"
    params = []
    
    if min_price:
        query += " AND w.price >= ?"
        params.append(float(min_price))
    if max_price:
        query += " AND w.price <= ?"
        params.append(float(max_price))
        
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    html = "<html><body><table border='1'><tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr>"
    for row in rows:
        html += f"<tr><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td><td>{row[3]}</td></tr>"
    html += "</table></body></html>"
    
    return web.Response(text=html, content_type='text/html')

# App setup
app = web.Application(middlewares=[auth_middleware])
app.add_routes([
    web.post('/merchants/register', register),
    web.post('/merchants/login', login),
    web.post('/merchants/upload-wares', upload_wares),
    web.get('/wares', get_wares),
])

if __name__ == '__main__':
    init_db()
    web.run_app(app, host='0.0.0.0', port=5000)