import os
import sqlite3
import csv
import io
from flask import Flask, request, jsonify, make_response, render_template_string, redirect, url_for, abort
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

app = Flask(__name__)
# Ensure secret key is robust
app.secret_key = os.environ.get("APP_SECRET", "fallback_secure_random_string_123456789")

# Database initialization
DB_NAME = "db.sqlite3"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS merchants (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, name TEXT, password TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS wares (id INTEGER PRIMARY KEY AUTOINCREMENT, merchant_id INTEGER, name TEXT, description TEXT, price REAL, FOREIGN KEY(merchant_id) REFERENCES merchants(id))")
        conn.commit()

init_db()

# Session management using itsdangerous (HMAC signed tokens)
serializer = URLSafeTimedSerializer(app.secret_key)

def set_auth_cookie(response, merchant_id):
    token = serializer.dumps(merchant_id)
    # Secure cookie flags: httponly to prevent XSS, samesite to prevent CSRF
    response.set_cookie("AUTH_COOKIE", token, httponly=True, samesite='Lax')

def get_merchant_id_from_cookie():
    token = request.cookies.get("AUTH_COOKIE")
    if not token:
        return None
    try:
        # Verify signature and expiry (24 hours)
        return serializer.loads(token, max_age=3600 * 24)
    except (BadSignature, SignatureExpired):
        return None

# HTML Templates - Using Jinja2's auto-escaping for XSS prevention
BASE_LAYOUT = """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Warehouse</title><style>
    body { font-family: sans-serif; margin: 20px; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
    .nav { margin-bottom: 20px; }
</style></head>
<body>
    <div class="nav">
        <a href="{{ url_for('get_wares') }}">View Wares</a> | 
        <a href="{{ url_for('register_page') }}">Register</a> | 
        <a href="{{ url_for('login_page') }}">Login</a> | 
        <a href="{{ url_for('upload_page') }}">Upload Wares</a> | 
        <a href="{{ url_for('logout') }}">Logout</a>
    </div>
    {% block content %}{% endblock %}
</body>
</html>
"""

WARE_LIST_TEMPLATE = """
{% extends "base" %}
{% block content %}
<h2>Available Wares</h2>
<form method="GET" action="{{ url_for('get_wares') }}">
    Min Price: <input type="number" step="0.01" name="minPrice"> 
    Max Price: <input type="number" step="0.01" name="maxPrice"> 
    <button type="submit">Filter</button>
</form>
<br>
<table>
    <tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr>
    {% for ware in wares %}
    <tr>
        <td>{{ ware.name }}</td>
        <td>{{ ware.price }}</td>
        <td>{{ ware.description }}</td>
        <td>{{ ware.merchant_email }}</td>
    </tr>
    {% endfor %}
</table>
{% endblock %}
"""

REGISTER_TEMPLATE = """
{% extends "base" %}
{% block content %}
<h2>Merchant Registration</h2>
<form method="POST" action="{{ url_for('register') }}">
    Name: <input type="text" name="name" required><br>
    Email: <input type="email" name="email" required><br>
    Password: <input type="password" name="password" required><br>
    <button type="submit">Register</button>
</form>
{% endblock %}
"""

LOGIN_TEMPLATE = """
{% extends "base" %}
{% block content %}
<h2>Merchant Login</h2>
<form method="POST" action="{{ url_for('login') }}">
    Email: <input type="email" name="email" required><br>
    Password: <input type="password" name="password" required><br>
    <button type="submit">Login</button>
</form>
{% endblock %}
"""

UPLOAD_TEMPLATE = """
{% extends "base" %}
{% block content %}
<h2>Upload Wares (CSV)</h2>
<p>Format: name, description, price (one per line)</p>
<form method="POST" action="{{ url_for('upload_wares') }}">
    <textarea name="csv" rows="10" cols="50" required></textarea><br>
    <button type="submit">Upload</button>
</form>
{% endblock %}
"""

@app.context_processor
def inject_base():
    return {'base': BASE_LAYOUT}

@app.route('/')
def index():
    return redirect(url_for('get_wares'))

@app.route('/register_page')
def register_page():
    return render_template_string(REGISTER_TEMPLATE)

@app.route('/login_page')
def login_page():
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/upload_page')
def upload_page():
    return render_template_string(UPLOAD_TEMPLATE)

@app.route('/logout')
def logout():
    resp = make_response(redirect(url_for('index')))
    resp.set_cookie("AUTH_COOKIE", "", expires=0)
    return resp

@app.route('/merchants/register', methods=['POST'])
def register():
    # Support both JSON and Form data as per OpenAPI spec
    data = request.get_json() if request.is_json else request.form
    if not data:
        return jsonify({"error": "Invalid input"}), 400
        
    email = data.get('email')
    name = data.get('name')
    password = data.get('password')

    if not all([email, name, password]):
        return jsonify({"error": "Invalid input"}), 400

    try:
        with get_db() as conn:
            # PBKDF2 via Werkzeug is a strong salted KDF
            hashed_pw = generate_password_hash(password)
            conn.execute("INSERT INTO merchants (email, name, password) VALUES (?, ?, ?)", (email, name, hashed_pw))
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already exists"}), 400
    except Exception:
        return jsonify({"error": "Internal server error"}), 400

    return jsonify({"message": "Merchant registered successfully"}), 201

@app.route('/merchants/login', methods=['POST'])
def login():
    data = request.get_json() if request.is_json else request.form
    if not data:
        return jsonify({"error": "Invalid input"}), 401
        
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Invalid email or password"}), 401

    with get_db() as conn:
        # Parameterized query to prevent SQL Injection
        merchant = conn.execute("SELECT * FROM merchants WHERE email = ?", (email,)).fetchone()
    
    # check_password_hash uses constant-time comparison
    if merchant and check_password_hash(merchant['password'], password):
        resp = make_response(jsonify("Login successful"), 200)
        set_auth_cookie(resp, merchant['id'])
        return resp
    
    return jsonify({"error": "Invalid email or password"}), 401

@app.route('/merchants/upload-wares', methods=['POST'])
def upload_wares():
    merchant_id = get_merchant_id_from_cookie()
    if not merchant_id:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() if request.is_json else request.form
    if not data:
        return jsonify({"error": "Invalid input"}), 400
        
    csv_text = data.get('csv', '')
    
    # Resource exhaustion: bound the input size for the CSV string
    if len(csv_text) > 100000: # 100KB limit
        return jsonify({"error": "CSV input too large"}), 400

    try:
        f = io.StringIO(csv_text)
        reader = csv.reader(f)
        with get_db() as conn:
            for row in reader:
                if not row: continue
                if len(row) != 3:
                    return jsonify({"error": "Invalid CSV format"}), 400
                
                name, desc, price_str = row
                try:
                    price = float(price_str)
                except ValueError:
                    return jsonify({"error": "Invalid price format"}), 400
                
                # Parameterized query to prevent SQL Injection
                conn.execute("INSERT INTO wares (merchant_id, name, description, price) VALUES (?, ?, ?, ?)", 
                             (merchant_id, name, desc, price))
            conn.commit()
    except Exception:
        return jsonify({"error": "Invalid CSV format"}), 400

    return jsonify({"message": "Wares uploaded successfully"}), 200

@app.route('/wares', methods=['GET'])
def get_wares():
    # Validate query parameters to prevent injection/errors
    try:
        min_price = request.args.get('minPrice', type=float)
        max_price = request.args.get('maxPrice', type=float)
    except ValueError:
        abort(400)

    # Parameterized query to prevent SQL Injection
    query = """
        SELECT w.name, w.price, w.description, m.email as merchant_email 
        FROM wares w JOIN merchants m ON w.merchant_id = m.id 
        WHERE 1=1
    """
    params = []
    if min_price is not None:
        query += " AND w.price >= ?"
        params.append(min_price)
    if max_price is not None:
        query += " AND w.price <= ?"
        params.append(max_price)

    with get_db() as conn:
        wares = conn.execute(query, params).fetchall()

    # render_template_string with Jinja2 automatically escapes content to prevent XSS
    return render_template_string(WARE_LIST_TEMPLATE, wares=wares)

if __name__ == '__main__':
    # Port 5000 as requested
    app.run(host='0.0.0.0', port=5000)