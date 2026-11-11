import os
import sqlite3
import csv
import io
from flask import Flask, request, jsonify, make_response, render_template_string, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key_12345")

# Database initialization
DB_NAME = "db.sqlite3"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS merchants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS wares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                FOREIGN KEY (merchant_id) REFERENCES merchants (id)
            )
        ''')
        conn.commit()

init_db()

# Auth helper
serializer = URLSafeTimedSerializer(app.secret_key)

def create_auth_cookie(merchant_id):
    return serializer.dumps(merchant_id)

def get_merchant_id_from_cookie(cookie_val):
    try:
        return serializer.loads(cookie_val)
    except:
        return None

# HTML Templates
BASE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Merchant Warehouse</title>
    <style>
        body { font-family: sans-serif; margin: 20px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        .nav { margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="nav">
        <a href="/wares">View Wares</a> | 
        <a href="/login_page">Login</a> | 
        <a href="/register_page">Register</a>
    </div>
    {% block content %}{% endblock %}
</body>
</html>
"""

LOGIN_PAGE = """
{% extends "base" %}
{% block content %}
<h2>Merchant Login</h2>
<form method="POST" action="/merchants/login">
    Email: <input type="email" name="email" required><br>
    Password: <input type="password" name="password" required><br>
    <button type="submit">Login</button>
</form>
{% endblock %}
"""

REGISTER_PAGE = """
{% extends "base" %}
{% block content %}
<h2>Merchant Registration</h2>
<form method="POST" action="/merchants/register">
    Name: <input type="text" name="name" required><br>
    Email: <input type="email" name="email" required><br>
    Password: <input type="password" name="password" required><br>
    <button type="submit">Register</button>
</form>
{% endblock %}
"""

UPLOAD_PAGE = """
{% extends "base" %}
{% block content %}
<h2>Upload Wares (CSV)</h2>
<p>Format: name, description, price (one per line)</p>
<form method="POST" action="/merchants/upload-wares">
    <textarea name="csv" rows="10" cols="50" required></textarea><br>
    <button type="submit">Upload</button>
</form>
{% endblock %}
"""

@app.context_processor
def inject_templates():
    return {
        'base_template': BASE_TEMPLATE,
        'login_page': LOGIN_PAGE,
        'register_page': REGISTER_PAGE,
        'upload_page': UPLOAD_PAGE
    }

# Routes for UI pages
@app.route('/login_page')
def login_page():
    return render_template_string(LOGIN_PAGE)

@app.route('/register_page')
def register_page():
    return render_template_string(REGISTER_PAGE)

@app.route('/upload_page')
def upload_page():
    auth_cookie = request.cookies.get('AUTH_COOKIE')
    if not get_merchant_id_from_cookie(auth_cookie):
        return redirect(url_for('login_page'))
    return render_template_string(UPLOAD_PAGE)

# API Endpoints
@app.route('/merchants/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not all(k in data for k in ('email', 'name', 'password')):
        return jsonify({"error": "Invalid input"}), 400
    
    hashed_pw = generate_password_hash(data['password'])
    try:
        with get_db_connection() as conn:
            conn.execute('INSERT INTO merchants (email, name, password) VALUES (?, ?, ?)', 
                         (data['email'], data['name'], hashed_pw))
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already exists"}), 400
    
    return jsonify({"message": "Merchant registered successfully"}), 201

@app.route('/merchants/login', methods=['POST'])
def login():
    # Support both JSON and Form data for the UI
    data = request.get_json() if request.is_json else request.form
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"error": "Missing credentials"}), 401

    with get_db_connection() as conn:
        merchant = conn.execute('SELECT * FROM merchants WHERE email = ?', (email,)).fetchone()
        
    if merchant and check_password_hash(merchant['password'], password):
        resp = make_response(jsonify("Login successful"))
        resp.set_cookie('AUTH_COOKIE', create_auth_cookie(merchant['id']))
        return resp
    
    return jsonify({"error": "Invalid email or password"}), 401

@app.route('/merchants/upload-wares', methods=['POST'])
def upload_wares():
    auth_cookie = request.cookies.get('AUTH_COOKIE')
    merchant_id = get_merchant_id_from_cookie(auth_cookie)
    if not merchant_id:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() if request.is_json else request.form
    csv_content = data.get('csv', '')
    
    try:
        f = io.StringIO(csv_content)
        reader = csv.reader(f)
        with get_db_connection() as conn:
            for row in reader:
                if not row: continue
                if len(row) != 3:
                    return jsonify({"error": "Invalid CSV format"}), 400
                name, desc, price = row
                conn.execute('INSERT INTO wares (merchant_id, name, description, price) VALUES (?, ?, ?, ?)', 
                             (merchant_id, name, desc, float(price)))
            conn.commit()
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"message": "Wares uploaded successfully"}), 200

@app.route('/wares', methods=['GET'])
def get_wares():
    min_price = request.args.get('minPrice', type=float)
    max_price = request.args.get('maxPrice', type=float)
    
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

    with get_db_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    # Render as HTML table
    table_html = "<table><tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr>"
    for row in rows:
        table_html += f"<tr><td>{row['name']}</td><td>{row['price']}</td><td>{row['description']}</td><td>{row['email']}</td></tr>"
    table_html += "</table>"
    
    # Wrap in base template
    return render_template_string(BASE_TEMPLATE.replace('{% block content %}{% endblock %}', table_html))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)