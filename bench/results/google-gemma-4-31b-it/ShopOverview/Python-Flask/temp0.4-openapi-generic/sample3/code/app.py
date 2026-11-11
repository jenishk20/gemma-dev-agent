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
def get_db_connection():
    conn = sqlite3.connect('db.sqlite3')
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

# Auth helper
serializer = URLSafeTimedSerializer(app.secret_key)

def create_auth_cookie(merchant_id):
    return serializer.dumps(merchant_id)

def get_merchant_id_from_cookie(cookie_val):
    try:
        return serializer.loads(cookie_val, max_age=3600 * 24) # 24h
    except:
        return None

# HTML Templates
LAYOUT_TPL = """
<!DOCTYPE html>
<html>
<head>
    <title>Warehouse</title>
    <style>
        body { font-family: sans-serif; margin: 20px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        .nav { margin-bottom: 20px; }
        .error { color: red; }
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

LOGIN_TPL = LAYOUT_TPL.replace('{% block content %}{% endblock %}', '''
    <h2>Merchant Login</h2>
    <form method="POST" action="/merchants/login">
        Email: <input type="email" name="email" required><br><br>
        Password: <input type="password" name="password" required><br><br>
        <button type="submit">Login</button>
    </form>
''')

REGISTER_TPL = LAYOUT_TPL.replace('{% block content %}{% endblock %}', '''
    <h2>Merchant Registration</h2>
    <form method="POST" action="/merchants/register">
        Name: <input type="text" name="name" required><br><br>
        Email: <input type="email" name="email" required><br><br>
        Password: <input type="password" name="password" required><br><br>
        <button type="submit">Register</button>
    </form>
''')

UPLOAD_TPL = LAYOUT_TPL.replace('{% block content %}{% endblock %}', '''
    <h2>Upload Wares</h2>
    <p>Enter CSV data (name, description, price)</p>
    <form method="POST" action="/merchants/upload-wares">
        <textarea name="csv" rows="10" cols="50" placeholder="Item1,Desc1,10.00\nItem2,Desc2,20.00"></textarea><br>
        <button type="submit">Upload</button>
    </form>
''')

# API Routes
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
        return jsonify({"error": "Email already registered"}), 400
    
    return jsonify({"message": "Merchant registered successfully"}), 201

@app.route('/merchants/login', methods=['POST'])
def login():
    # Support both JSON and Form for the webapp
    data = request.get_json() if request.is_json else request.form
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Missing credentials"}), 401

    with get_db_connection() as conn:
        user = conn.execute('SELECT id, password FROM merchants WHERE email = ?', (email,)).fetchone()
        if user and check_password_hash(user['password'], password):
            resp = make_response(jsonify("Login successful"), 200)
            resp.set_cookie('AUTH_COOKIE', create_auth_cookie(user['id']), httponly=True)
            return resp
    
    return jsonify({"error": "Invalid email or password"}), 401

@app.route('/merchants/upload-wares', methods=['POST'])
def upload_wares():
    merchant_id = get_merchant_id_from_cookie(request.cookies.get('AUTH_COOKIE'))
    if not merchant_id:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() if request.is_json else request.form
    csv_text = data.get('csv', '')
    
    try:
        f = io.StringIO(csv_text)
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
    except (ValueError, csv.Error):
        return jsonify({"error": "Invalid CSV format"}), 400

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
        wares = conn.execute(query, params).fetchall()

    table_html = "<table><tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr>"
    for w in wares:
        table_html += f"<tr><td>{w['name']}</td><td>{w['price']}</td><td>{w['description']}</td><td>{w['email']}</td></tr>"
    table_html += "</table>"
    
    # For the API requirement, we return HTML. For the webapp, we wrap it in layout.
    return render_template_string(LAYOUT_TPL.replace('{% block content %}{% endblock %}', f'''
        <h2>Available Wares</h2>
        <form method="GET" action="/wares">
            Min Price: <input type="number" step="0.01" name="minPrice"> 
            Max Price: <input type="number" step="0.01" name="maxPrice"> 
            <button type="submit">Filter</button>
        </form>
        <br>
        {table_html}
    '''))

# UI Helper Routes
@app.route('/login_page')
def login_page():
    return render_template_string(LOGIN_TPL)

@app.route('/register_page')
def register_page():
    return render_template_string(REGISTER_TPL)

@app.route('/upload_page')
def upload_page():
    merchant_id = get_merchant_id_from_cookie(request.cookies.get('AUTH_COOKIE'))
    if not merchant_id:
        return redirect(url_for('login_page'))
    return render_template_string(UPLOAD_TPL)

# Redirect login success to upload page for better UX
@app.route('/login', methods=['POST'])
def login_redirect():
    # This is a helper for the HTML form
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    # The OpenAPI spec says /merchants/login is POST. 
    # To make the HTML form work, we can use a custom handler or just use the API route.
    # Since the API route returns JSON, we'll wrap the HTML form to use JS or just accept JSON.
    # For simplicity in this single-file app, we'll make the API routes handle both.
    app.run(host='0.0.0.0', port=5000)