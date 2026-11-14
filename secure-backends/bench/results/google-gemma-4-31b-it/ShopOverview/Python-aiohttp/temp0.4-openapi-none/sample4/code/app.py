import os
import sqlite3
import csv
import io
import jwt
import datetime
from aiohttp import web
from passlib.hash import pbkdf2_sha256

# Configuration
DB_PATH = 'db.sqlite3'
APP_SECRET = os.environ.get('APP_SECRET', 'default_secret_key_change_me')
COOKIE_NAME = 'AUTH_COOKIE'

# Database Initialization
def init_db():
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Auth Helpers
def create_token(email):
    payload = {
        'email': email,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    return jwt.encode(payload, APP_SECRET, algorithm='HS256')

def verify_token(token):
    try:
        payload = jwt.decode(token, APP_SECRET, algorithms=['HS256'])
        return payload['email']
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
            return web.Response(text="Invalid input", status=400)

        hashed_pw = pbkdf2_sha256.hash(password)
        
        conn = get_db_conn()
        try:
            conn.execute('INSERT INTO merchants (email, name, password) VALUES (?, ?, ?)', 
                         (email, name, hashed_pw))
            conn.commit()
        except sqlite3.IntegrityError:
            return web.Response(text="Merchant already exists", status=400)
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

        conn = get_db_conn()
        user = conn.execute('SELECT * FROM merchants WHERE email = ?', (email,)).fetchone()
        conn.close()

        if user and pbkdf2_sha256.verify(password, user['password']):
            token = create_token(email)
            resp = web.json_response("Login successful")
            resp.set_cookie(COOKIE_NAME, token, httponly=True)
            return resp
        
        return web.json_response({"error": "Invalid email or password"}, status=401)
    except Exception:
        return web.json_response({"error": "Invalid request"}, status=400)

async def upload_wares(request):
    token = request.cookies.get(COOKIE_NAME)
    email = verify_token(token) if token else None
    if not email:
        return web.Response(status=401)

    try:
        data = await request.json()
        csv_content = data.get('csv', '')
        
        f = io.StringIO(csv_content)
        reader = csv.reader(f)
        
        conn = get_db_conn()
        merchant = conn.execute('SELECT id FROM merchants WHERE email = ?', (email,)).fetchone()
        m_id = merchant['id']

        rows_added = 0
        for row in reader:
            if len(row) != 3:
                conn.close()
                return web.Response(text="Invalid CSV format", status=400)
            name, desc, price_str = row
            price = float(price_str)
            conn.execute('INSERT INTO wares (merchant_id, name, description, price) VALUES (?, ?, ?, ?)', 
                         (m_id, name, desc, price))
            rows_added += 1
        
        conn.commit()
        conn.close()
        return web.Response(status=200)
    except (ValueError, csv.Error):
        return web.Response(text="Invalid CSV format", status=400)
    except Exception as e:
        return web.Response(text=str(e), status=400)

async def get_wares(request):
    token = request.cookies.get(COOKIE_NAME)
    email = verify_token(token) if token else None
    if not email:
        return web.Response(status=401)

    min_price = request.query.get('minPrice', type=float)
    max_price = request.query.get('maxPrice', type=float)

    query = '''
        SELECT w.name, w.price, w.description, m.email 
        FROM wares w 
        JOIN merchants m ON w.merchant_id = m.id 
        WHERE 1=1
    '''
    params = []
    if min_price is not None:
        query += " AND w.price >= ?"
        params.append(min_price)
    if max_price is not None:
        query += " AND w.price <= ?"
        params.append(max_price)

    conn = get_db_conn()
    rows = conn.execute(query, params).fetchall()
    conn.close()

    html = "<html><body><table>"
    html += "<tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr>"
    for row in rows:
        html += f"<tr><td>{row['name']}</td><td>{row['price']}</td><td>{row['description']}</td><td>{row['email']}</td></tr>"
    html += "</table></body></html>"
    
    return web.Response(text=html, content_type='text/html')

app = web.Application()
app.add_routes([
    web.post('/merchants/register', register),
    web.post('/merchants/login', login),
    web.post('/merchants/upload-wares', upload_wares),
    web.get('/wares', get_wares),
])

if __name__ == '__main__':
    init_db()
    web.run_app(app, host='0.0.0.0', port=5000)