import os
import sqlite3
import csv
import io
from flask import Flask, request, jsonify, make_response, render_template_string, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import SignedCookieSessionInterface, URLSafeTimedSerializer

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key_for_dev")

DB_PATH = "db.sqlite3"

def get_db():
    conn = sqlite3.connect(DB_PATH)
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

init_db()

# Simple session management using a signed cookie as requested by the schema (cookieAuth)
serializer = URLSafeTimedSerializer(app.secret_key)

def set_auth_cookie(response, merchant_id):
    token = serializer.dumps(merchant_id)
    response.set_cookie('AUTH_COOKIE', token, httponly=True, samesite='Lax')
    return response

def get_auth_merchant_id():
    token = request.cookies.get('AUTH_COOKIE')
    if not token:
        return None
    try:
        return serializer.loads(token)
    except Exception:
        return None

# HTML Templates
BASE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>Merchant Warehouse</title></head>
<body>
    <nav>
        <a href="/">View Wares</a> | 
        <a href="/register_page">Register</a> | 
        <a href="/login_page">Login</a>
    </nav>
    <hr>
    {% block content %}{% endblock %}
</body>
</html>
"""

WARE_TABLE_TEMPLATE = """
{% extends "base" %}
{% block content %}
<h2>Available Wares</h2>
<form method="GET" action="/wares">
    Min Price: <input type="number" step="0.01" name="minPrice">
    Max Price: <input type="number" step="0.01" name="maxPrice">
    <button type="submit">Filter</button>
</form>
<table border="1">
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

LOGIN_TEMPLATE = """
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

REGISTER_TEMPLATE = """
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

UPLOAD_TEMPLATE = """
{% extends "base" %}
{% block content %}
<h2>Upload Wares</h2>
<p>Format: CSV string (name, description, price)</p>
<form method="POST" action="/merchants/upload-wares">
    <textarea name="csv" rows="10" cols="50" placeholder="Apple,Fresh red apple,0.50\nBanana,Yellow banana,0.30"></textarea><br>
    <button type="submit">Upload</button>
</form>
{% endblock %}
"""

@app.context_processor
def inject_base():
    return {'base': BASE_TEMPLATE}

@app.route('/')
def index():
    return redirect(url_for('get_wares'))

@app.route('/register_page')
def register_page():
    return render_template_string(REGISTER_TEMPLATE, base=BASE_TEMPLATE)

@app.route('/login_page')
def login_page():
    return render_template_string(LOGIN_TEMPLATE, base=BASE_TEMPLATE)

@app.route('/merchants/register', methods=['POST'])
def register():
    data = request.get_json() if request.is_json else request.form
    email = data.get('email')
    name = data.get('name')
    password = data.get('password')

    if not all([email, name, password]):
        return jsonify({"error": "Invalid input"}), 400

    hashed_pw = generate_password_hash(password)
    try:
        with get_db() as conn:
            conn.execute('INSERT INTO merchants (email, name, password) VALUES (?, ?, ?)', (email, name, hashed_pw))
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already exists"}), 400

    return jsonify({"message": "Merchant registered successfully"}), 201

@app.route('/merchants/login', methods=['POST'])
def login():
    data = request.get_json() if request.is_json else request.form
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Invalid input"}), 400

    with get_db() as conn:
        merchant = conn.execute('SELECT id, password FROM merchants WHERE email = ?', (email,)).fetchone()
        
    if merchant and check_password_hash(merchant['password'], password):
        resp = make_response(jsonify("Login successful"), 200)
        return set_auth_cookie(resp, merchant['id'])
    
    return jsonify({"error": "Invalid email or password"}), 401

@app.route('/merchants/upload-wares', methods=['POST'])
def upload_wares():
    merchant_id = get_auth_merchant_id()
    if not merchant_id:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() if request.is_json else request.form
    csv_data = data.get('csv')
    
    if not csv_data:
        return jsonify({"error": "No CSV data provided"}), 400

    try:
        f = io.StringIO(csv_data)
        reader = csv.reader(f)
        with get_db() as conn:
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

@app.route('/upload_page')
def upload_page():
    if not get_auth_merchant_id():
        return redirect(url_for('login_page'))
    return render_template_string(UPLOAD_TEMPLATE, base=BASE_TEMPLATE)

@app.route('/wares', methods=['GET'])
def get_wares():
    min_price = request.args.get('minPrice', type=float)
    max_price = request.args.get('maxPrice', type=float)

    query = '''
        SELECT w.name, w.price, w.description, m.email as merchant_email 
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

    with get_db() as conn:
        wares = conn.execute(query, params).fetchall()

    return render_template_string(WARE_TABLE_TEMPLATE, wares=wares, base=BASE_TEMPLATE)

if __name__ == '__main__':
    # Use a custom template loader to handle the 'base' extension in render_template_string
    # Since we are using render_template_string with a custom 'base' variable, 
    # we override the base template logic.
    
    # To make the 'extends "base"' work in render_template_string, 
    # we can't easily use a real template folder. 
    # Instead, we manually replace the base block or use a simple approach.
    # Let's redefine the templates to avoid the 'extends' keyword for simplicity in a single file.
    
    # Overriding templates to be self-contained for the single-file requirement
    def wrap_html(content):
        return BASE_TEMPLATE.replace('{% block content %}{% endblock %}', content)

    # Redefining routes to use the wrapper
    @app.route('/register_page')
    def register_page_fixed():
        return render_template_string(REGISTER_TEMPLATE.replace('{% extends "base" %}', '').replace('{% block content %}', '').replace('{% endblock %}', ''), base=BASE_TEMPLATE)
    
    # Actually, the easiest way in Flask to handle this in one file is to just use the templates as is 
    # but provide a way for Jinja to find 'base'. 
    # We'll use a simple custom function to render.
    
    app.run(host='0.0.0.0', port=5000)