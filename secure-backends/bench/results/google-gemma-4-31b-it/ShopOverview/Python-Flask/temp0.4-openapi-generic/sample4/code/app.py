import os
import sqlite3
import csv
import io
from flask import Flask, request, jsonify, make_response, render_template_string, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key_for_dev")

# Database helper
def get_db():
    conn = sqlite3.connect('db.sqlite3')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
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

# Auth helper
serializer = URLSafeTimedSerializer(app.secret_key)

def create_auth_cookie(merchant_id):
    return serializer.dumps(merchant_id)

def get_merchant_from_cookie():
    token = request.cookies.get('AUTH_COOKIE')
    if not token:
        return None
    try:
        merchant_id = serializer.loads(token, max_age=3600 * 24)
        return merchant_id
    except Exception:
        return None

# HTML Templates
LAYOUT = """
<!DOCTYPE html>
<html>
<head>
    <title>Warehouse App</title>
    <style>
        body { font-family: sans-serif; margin: 20px; }
        nav { margin-bottom: 20px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        .error { color: red; }
    </style>
</head>
<body>
    <nav>
        <a href="/">View Wares</a> | 
        <a href="/login_page">Login</a> | 
        <a href="/register_page">Register</a> | 
        <a href="/upload_page">Upload Wares</a>
    </nav>
    {% block content %}{% endblock %}
</body>
</html>
"""

LOGIN_HTML = """
{% extends "layout" %}
{% block content %}
    <h2>Merchant Login</h2>
    <form method="POST" action="/merchants/login">
        Email: <input type="email" name="email" required><br>
        Password: <input type="password" name="password" required><br>
        <button type="submit">Login</button>
    </form>
{% endblock %}
"""

REGISTER_HTML = """
{% extends "layout" %}
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

UPLOAD_HTML = """
{% extends "layout" %}
{% block content %}
    <h2>Upload Wares</h2>
    <p>Format: name,description,price (one per line)</p>
    <form method="POST" action="/merchants/upload-wares">
        <textarea name="csv" rows="10" cols="50" required></textarea><br>
        <button type="submit">Upload</button>
    </form>
{% endblock %}
"""

WARES_HTML = """
{% extends "layout" %}
{% block content %}
    <h2>Available Wares</h2>
    <form method="GET" action="/wares">
        Min Price: <input type="number" step="0.01" name="minPrice">
        Max Price: <input type="number" step="0.01" name="maxPrice">
        <button type="submit">Filter</button>
    </form>
    <br>
    <table>
        <thead>
            <tr>
                <th>Name</th>
                <th>Price</th>
                <th>Description</th>
                <th>Merchant</th>
            </tr>
        </thead>
        <tbody>
            {% for ware in wares %}
            <tr>
                <td>{{ ware.name }}</td>
                <td>{{ ware.price }}</td>
                <td>{{ ware.description }}</td>
                <td>{{ ware.merchant_email }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
{% endblock %}
"""

@app.route('/layout')
def layout():
    return LAYOUT

@app.route('/login_page')
def login_page():
    return render_template_string(LOGIN_HTML), 200, {'layout': LAYOUT}

@app.route('/register_page')
def register_page():
    return render_template_string(REGISTER_HTML), 200, {'layout': LAYOUT}

@app.route('/upload_page')
def upload_page():
    mid = get_merchant_from_cookie()
    if not mid:
        return redirect(url_for('login_page'))
    return render_template_string(UPLOAD_HTML), 200, {'layout': LAYOUT}

# API Endpoints
@app.route('/merchants/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not all(k in data for k in ('email', 'name', 'password')):
        return jsonify({"error": "Invalid input"}), 400
    
    pw_hash = generate_password_hash(data['password'])
    try:
        with get_db() as conn:
            conn.execute('INSERT INTO merchants (email, name, password) VALUES (?, ?, ?)', 
                         (data['email'], data['name'], pw_hash))
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already exists"}), 400
    
    return jsonify({"message": "Merchant registered successfully"}), 201

@app.route('/merchants/login', methods=['POST'])
def login():
    # Handle both JSON and Form data for convenience
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form
        
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"error": "Missing credentials"}), 401

    with get_db() as conn:
        merchant = conn.execute('SELECT id, password FROM merchants WHERE email = ?', (email,)).fetchone()
        
    if merchant and check_password_hash(merchant['password'], password):
        resp = make_response(jsonify("Login successful"))
        resp.set_cookie('AUTH_COOKIE', create_auth_cookie(merchant['id']))
        return resp
    
    return jsonify({"error": "Invalid email or password"}), 401

@app.route('/merchants/upload-wares', methods=['POST'])
def upload_wares():
    merchant_id = get_merchant_from_cookie()
    if not merchant_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json() if request.is_json else request.form
    csv_content = data.get('csv')
    if not csv_content:
        return jsonify({"error": "No CSV data provided"}), 400
    
    try:
        f = io.StringIO(csv_content)
        reader = csv.reader(f)
        with get_db() as conn:
            for row in reader:
                if not row: continue
                if len(row) != 3:
                    raise ValueError("Invalid column count")
                name, desc, price = row
                conn.execute('INSERT INTO wares (merchant_id, name, description, price) VALUES (?, ?, ?, ?)', 
                             (merchant_id, name, desc, float(price)))
            conn.commit()
    except Exception as e:
        return jsonify({"error": f"Invalid CSV format: {str(e)}"}), 400
    
    return jsonify({"message": "Wares uploaded successfully"}), 200

@app.route('/wares', methods=['GET'])
def get_wares():
    min_p = request.args.get('minPrice', type=float)
    max_p = request.args.get('maxPrice', type=float)
    
    query = '''
        SELECT w.name, w.price, w.description, m.email as merchant_email 
        FROM wares w JOIN merchants m ON w.merchant_id = m.id 
        WHERE 1=1
    '''
    params = []
    if min_p is not None:
        query += " AND w.price >= ?"
        params.append(min_p)
    if max_p is not None:
        query += " AND w.price <= ?"
        params.append(max_p)
        
    with get_db() as conn:
        wares = conn.execute(query, params).fetchall()
    
    # Render using the layout
    return render_template_string(WARES_HTML, wares=wares, layout=LAYOUT)

# Setup Jinja2 to handle the layout block
@app.context_processor
def inject_layout():
    return {'layout': LAYOUT}

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)