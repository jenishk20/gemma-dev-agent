import os
import sqlite3
import csv
import io
import jwt
import datetime
from aiohttp import web
from passlib.hash import pbkdf2_sha256

# Configuration
APP_SECRET = os.environ.get("APP_SECRET", "default_secret_key_12345")
DB_NAME = "db.sqlite3"

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

def get_db_conn():
    return sqlite3.connect(DB_NAME)

# Auth Helpers
def create_token(email):
    payload = {
        "email": email,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    return jwt.encode(payload, APP_SECRET, algorithm="HS256")

def verify_token(token):
    try:
        payload = jwt.decode(token, APP_SECRET, algorithms=["HS256"])
        return payload["email"]
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

# Handlers
async def register(request):
    try:
        data = await request.json()
        email = data.get('email')
        name = data.get('name')
        password = data.get('password')
        
        if not all([email, name, password]):
            return web.Response(status=400, text="Missing fields")
        
        hashed_pw = pbkdf2_sha256.hash(password)
        
        conn = get_db_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO merchants (email, name, password) VALUES (?, ?, ?)", 
                           (email, name, hashed_pw))
            conn.commit()
        except sqlite3.IntegrityError:
            return web.Response(status=400, text="Email already registered")
        finally:
            conn.close()
            
        return web.Response(status=201)
    except Exception:
        return web.Response(status=400)

async def login(request):
    try:
        data = await request.json()
        email = data.get('email')
        password = data.get('password')
        
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM merchants WHERE email = ?", (email,))
        row = cursor.fetchone()
        conn.close()
        
        if row and pbkdf2_sha256.verify(password, row[0]):
            token = create_token(email)
            resp = web.json_response("Login successful")
            resp.set_cookie("AUTH_COOKIE", token, httponly=True)
            return resp
        
        return web.json_response({"error": "Invalid email or password"}, status=401)
    except Exception:
        return web.Response(status=400)

async def upload_wares(request):
    token = request.cookies.get("AUTH_COOKIE")
    email = verify_token(token)
    if not email:
        return web.Response(status=401)
    
    try:
        data = await request.json()
        csv_content = data.get('csv', '')
        
        f = io.StringIO(csv_content)
        reader = csv.DictReader(f, fieldnames=["name", "description", "price"])
        
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM merchants WHERE email = ?", (email,))
        m_id = cursor.fetchone()[0]
        
        for row in reader:
            if not row['name'] or not row['price']:
                conn.close()
                return web.Response(status=400, text="Invalid CSV format")
            cursor.execute("INSERT INTO wares (merchant_id, name, description, price) VALUES (?, ?, ?, ?)",
                           (m_id, row['name'], row['description'], float(row['price'])))
        
        conn.commit()
        conn.close()
        return web.Response(status=200)
    except Exception:
        return web.Response(status=400)

async def list_wares(request):
    token = request.cookies.get("AUTH_COOKIE")
    if not verify_token(token):
        return web.Response(status=401)
    
    min_price = request.query.get('minPrice', 0)
    max_price = request.query.get('maxPrice', float('inf'))
    
    try:
        min_p = float(min_price)
        max_p = float(max_price)
    except ValueError:
        return web.Response(status=400)

    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT w.name, w.price, w.description, m.email 
        FROM wares w 
        JOIN merchants m ON w.merchant_id = m.id 
        WHERE w.price >= ? AND w.price <= ?
    ''', (min_p, max_p))
    rows = cursor.fetchall()
    conn.close()
    
    html = "<html><body><table>"
    html += "<tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr>"
    for row in rows:
        html += f"<tr><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td><td>{row[3]}</td></tr>"
    html += "</table></body></html>"
    
    return web.Response(text=html, content_type='text/html')

# App Setup
app = web.Application()
app.add_routes([
    web.post('/merchants/register', register),
    web.post('/merchants/login', login),
    web.post('/merchants/upload-wares', upload_wares),
    web.get('/wares', list_wares),
])

if __name__ == "__main__":
    init_db()
    web.run_app(app, host='0.0.0.0', port=5000)