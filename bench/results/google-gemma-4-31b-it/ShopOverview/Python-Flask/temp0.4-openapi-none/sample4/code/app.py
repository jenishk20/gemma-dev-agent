import os
import sqlite3
import csv
import io
from flask import Flask, request, jsonify, make_response, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key")
serializer = URLSafeTimedSerializer(app.secret_key)

DB_NAME = "db.sqlite3"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS merchants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password TEXT NOT NULL
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS wares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            merchant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            FOREIGN KEY (merchant_id) REFERENCES merchants (id)
        )''')
        conn.commit()

@app.before_first_request
def setup():
    init_db()

# Helper for authentication
def get_authenticated_user():
    token = request.cookies.get("AUTH_COOKIE")
    if not token:
        return None
    try:
        email = serializer.loads(token, max_age=3600)
        return email
    except Exception:
        return None

# HTML Templates
BASE_LAYOUT = """
<!DOCTYPE html>
<html>
<head>
    <title>Merchant Warehouse</title>
    <style>
        body { font-family: sans-serif; margin: 20px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
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

LOGIN_HTML = """
{% extends "base" %}
{% block content %}
<h2>Merchant Login</h2>
<form method="POST" action="/merchants/login">
    Email: <input type="email" name="email" required><br><br>
    Password: <input type="password" name="password" required><br><br>
    <button type="submit">Login</button>
</form>
{% endblock %}
"""

REGISTER_HTML = """
{% extends "base" %}
{% block content %}
<h2>Merchant Registration</h2>
<form method="POST" action="/merchants/register">
    Name: <input type="text" name="name" required><br><br>
    Email: <input type="email" name="email" required><br><br>
    Password: <input type="password" name="password" required><br><br>
    <button type="submit">Register</button>
</form>
{% endblock %}
"""

UPLOAD_HTML = """
{% extends "base" %}
{% block content %}
<h2>Upload Wares</h2>
<p>Format: name,description,price (one per line)</p>
<form method="POST" action="/merchants/upload-wares">
    <textarea name="csv" rows="10" cols="50" required></textarea><br><br>
    <button type="submit">Upload CSV</button>
</form>
{% endblock %}
"""

# Routes
@app.route('/')
def index():
    return render_template_string("<h2>Welcome to the Warehouse</h2><a href='/wares'>View Wares</a>")

@app.route('/login_page')
def login_page():
    return render_template_string(LOGIN_HTML, base=BASE_LAYOUT)

@app.route('/register_page')
def register_page():
    return render_template_string(REGISTER_HTML, base=BASE_LAYOUT)

@app.route('/upload_page')
def upload_page():
    if not get_authenticated_user():
        return "Unauthorized", 401
    return render_template_string(UPLOAD_HTML, base=BASE_LAYOUT)

@app.route('/merchants/register', methods=['POST'])
def register():
    data = request.get_json() if request.is_json else request.form
    email = data.get('email')
    name = data.get('name')
    password = data.get('password')

    if not all([email, name, password]):
        return jsonify({"error": "Invalid input"}), 400

    try:
        with get_db() as conn:
            conn.execute("INSERT INTO merchants (email, name, password) VALUES (?, ?, ?)",
                         (email, name, generate_password_hash(password)))
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already exists"}), 400

    return jsonify({"message": "Merchant registered successfully"}), 201

@app.route('/merchants/login', methods=['POST'])
def login():
    data = request.get_json() if request.is_json else request.form
    email = data.get('email')
    password = data.get('password')

    with get_db() as conn:
        user = conn.execute("SELECT * FROM merchants WHERE email = ?", (email,)).fetchone()

    if user and check_password_hash(user['password'], password):
        token = serializer.dumps(email)
        resp = make_response(jsonify("Login successful"))
        resp.set_cookie("AUTH_COOKIE", token)
        return resp

    return jsonify({"error": "Invalid email or password"}), 401

@app.route('/merchants/upload-wares', methods=['POST'])
def upload_wares():
    user_email = get_authenticated_user()
    if not user_email:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() if request.is_json else request.form
    csv_data = data.get('csv')
    if not csv_data:
        return jsonify({"error": "No CSV data provided"}), 400

    try:
        f = io.StringIO(csv_data)
        reader = csv.reader(f)
        with get_db() as conn:
            merchant = conn.execute("SELECT id FROM merchants WHERE email = ?", (user_email,)).fetchone()
            m_id = merchant['id']
            for row in reader:
                if len(row) != 3:
                    continue
                name, desc, price = row
                conn.execute("INSERT INTO wares (merchant_id, name, description, price) VALUES (?, ?, ?, ?)",
                             (m_id, name, desc, float(price)))
            conn.commit()
    except Exception as e:
        return jsonify({"error": f"Invalid CSV format: {str(e)}"}), 400

    return jsonify({"message": "Wares uploaded successfully"}), 200

@app.route('/wares', methods=['GET'])
def get_wares():
    min_price = request.args.get('minPrice', type=float)
    max_price = request.args.get('maxPrice', type=float)

    query = """
        SELECT w.name, w.price, w.description, m.email 
        FROM wares w 
        JOIN merchants m ON w.merchant_id = m.id 
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
        rows = conn.execute(query, params).fetchall()

    table_html = "<table><tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr>"
    for row in rows:
        table_html += f"<tr><td>{row['name']}</td><td>{row['price']}</td><td>{row['description']}</td><td>{row['email']}</td></tr>"
    table_html += "</table>"

    return render_template_string(f"""
    {{% extends "base" %}}
    {{% block content %}}
    <h2>Available Wares</h2>
    <form method="GET" action="/wares">
        Min Price: <input type="number" step="0.01" name="minPrice"> 
        Max Price: <input type="number" step="0.01" name="maxPrice"> 
        <button type="submit">Filter</button>
    </form>
    <br>
    {table_html}
    {{% endblock %}}
    """, base=BASE_LAYOUT)

@app.context_processor
def inject_base():
    return {'base': BASE_LAYOUT}

if __name__ == '__main__':
    # Manual trigger for DB init since @app.before_first_request is deprecated in newer Flask
    init_db()
    app.run(host='0.0.0.0', port=5000)