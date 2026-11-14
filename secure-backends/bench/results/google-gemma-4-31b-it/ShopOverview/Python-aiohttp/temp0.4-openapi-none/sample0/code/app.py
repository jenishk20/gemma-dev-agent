import os
import asyncio
import sqlite3
import csv
import io
import jwt
import datetime
from aiohttp import web
from passlib.hash import pbkdf2_sha256

# Configuration
DB_NAME = "db.sqlite3"
SECRET_KEY = os.environ.get("APP_SECRET", "default_secret_key_change_me")
COOKIE_NAME = "AUTH_COOKIE"

# Database setup
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
            merchant_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            FOREIGN KEY (merchant_id) REFERENCES merchants(id)
        )
    ''')
    conn.commit()
    conn.close()

def get_db_conn():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# Auth Helpers
def create_token(merchant_id):
    payload = {
        "merchant_id": merchant_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload["merchant_id"]
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

# Request Handlers
async def register(request):
    try:
        data = await request.json()
        email = data.get('email')
        name = data.get('name')
        password = data.get('password')

        if not all([email, name, password]):
            return web.json_response({"error": "Missing fields"}, status=400)

        hashed_pw = pbkdf2_sha256.hash(password)
        
        conn = get_db_conn()
        try:
            conn.execute("INSERT INTO merchants (email, name, password) VALUES (?, ?, ?)", 
                        (email, name, hashed_pw))
            conn.commit()
        except sqlite3.IntegrityError:
            return web.json_response({"error": "Merchant already exists"}, status=400)
        finally:
            conn.close()
            
        return web.Response(status=201)
    except Exception:
        return web.json_response({"error": "Invalid input"}, status=400)

async def login(request):
    try:
        data = await request.json()
        email = data.get('email')
        password = data.get('password')

        conn = get_db_conn()
        merchant = conn.execute("SELECT id, password FROM merchants WHERE email = ?", (email,)).fetchone()
        conn.close()

        if merchant and pbkdf2_sha256.verify(password, merchant['password']):
            token = create_token(merchant['id'])
            resp = web.json_response("Login successful")
            resp.set_cookie(COOKIE_NAME, token, httponly=True)
            return resp
        
        return web.json_response({"error": "Invalid email or password"}, status=401)
    except Exception:
        return web.json_response({"error": "Invalid request"}, status=400)

async def upload_wares(request):
    token = request.cookies.get(COOKIE_NAME)
    merchant_id = verify_token(token)
    if not merchant_id:
        return web.Response(status=401)

    try:
        data = await request.json()
        csv_text = data.get('csv', '')
        
        f = io.StringIO(csv_text)
        reader = csv.reader(f)
        
        conn = get_db_conn()
        try:
            for row in reader:
                if len(row) != 3:
                    raise ValueError("Invalid CSV format")
                name, description, price = row
                conn.execute("INSERT INTO wares (merchant_id, name, description, price) VALUES (?, ?, ?, ?)",
                            (merchant_id, name, description, float(price)))
            conn.commit()
        except Exception as e:
            return web.Response(status=400, text=str(e))
        finally:
            conn.close()
            
        return web.Response(status=200)
    except Exception:
        return web.Response(status=400)

async def get_wares(request):
    token = request.cookies.get(COOKIE_NAME)
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
    query = """
        SELECT w.name, w.price, w.description, m.email 
        FROM wares w 
        JOIN merchants m ON w.merchant_id = m.id 
        WHERE w.price >= ? AND w.price <= ?
    """
    rows = conn.execute(query, (min_p, max_p)).fetchall()
    conn.close()

    html = "<html><body><table>"
    html += "<tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr>"
    for row in rows:
        html += f"<tr><td>{row['name']}</td><td>{row['price']}</td><td>{row['description']}</td><td>{row['email']}</td></tr>"
    html += "</table></body></html>"
    
    return web.Response(text=html, content_type='text/html')

# App setup
app = web.Application()
app.add_routes([
    web.post('/merchants/register', register),
    web.post('/merchants/login', login),
    web.post('/merchants/upload-wares', upload_wares),
    web.get('/wares', get_wares),
])

if __name__ == "__main__":
    init_db()
    web.run_app(app, host='0.0.0.0', port=5000)