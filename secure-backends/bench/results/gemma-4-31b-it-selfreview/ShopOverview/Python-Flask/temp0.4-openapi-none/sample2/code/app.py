import os
import sqlite3
import csv
import io
from flask import Flask, request, jsonify, make_response, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

app = Flask(__name__)
# Use APP_SECRET from environment or a fallback for development
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key_for_dev_only")

# Database initialization
DB_NAME = "db.sqlite3"

def get_db():
    conn = sqlite3.connect(DB_NAME)
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

# Auth Serializer with expiry
serializer = URLSafeTimedSerializer(app.secret_key)

def create_token(user_id):
    return serializer.dumps(user_id)

def verify_token(token):
    if not token:
        return None
    try:
        # Set a reasonable expiry (e.g., 24 hours)
        return serializer.loads(token, max_age=86400)
    except (BadSignature, SignatureExpired):
        return None

# HTML Templates - Jinja2 automatically escapes variables passed to {{ }}
BASE_LAYOUT = """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Warehouse</title></head>
<body style="font-family: sans-serif;">
    <nav><a href="/wares">View Wares</a> | <a href="/login_page">Login</a> | <a href="/register_page">Register</a></nav>
    <hr>
    {% block content %}{% endblock %}
</body>
</html>
"""

WARES_TEMPLATE = BASE_LAYOUT + """
{% block content %}
<h2 style="color: #333;">Available Wares</h2>
<form method="GET" action="/wares">
    Min Price: <input type="number" step="0.01" name="minPrice">
    Max Price: <input type="number" step="0.01" name="maxPrice">
    <button type="submit">Filter</button>
</form>
<table border="1" style="border-collapse: collapse; margin-top: 20px;">
    <thead>
        <tr style="background-color: #eee;"><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr>
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

LOGIN_TEMPLATE = BASE_LAYOUT + """
{% block content %}
<h2>Merchant Login</h2>
<form method="POST" action="/merchants/login">
    Email: <input type="email" name="email" required><br>
    Password: <input type="password" name="password" required><br>
    <button type="submit">Login</button>
</form>
{% endblock %}
"""

REGISTER_TEMPLATE = BASE_LAYOUT + """
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

UPLOAD_TEMPLATE = BASE_LAYOUT + """
{% block content %}
<h2>Upload Wares</h2>
<p>Format: CSV string (name, description, price)</p>
<form method="POST" action="/merchants/upload-wares">
    <textarea name="csv" rows="10" cols="50" placeholder="Apple,Fresh red apple,1.50\nBanana,Sweet yellow banana,0.50"></textarea><br>
    <button type="submit">Upload</button>
</form>
{% endblock %}
"""

# API Routes

@app.route('/merchants/register', methods=['POST'])
def register():
    # Limit request size to prevent resource exhaustion
    if request.content_length > 10 * 1024: # 10KB
        return jsonify({"error": "Request too large"}), 400
        
    data = request.get_json(silent=True)
    if not data or not all(k in data for k in ('email', 'name', 'password')):
        return jsonify({"error": "Invalid input"}), 400
    
    # Basic validation for required fields
    if not all(isinstance(data[k], str) for k in ('email', 'name', 'password')):
        return jsonify({"error": "Invalid input"}), 400

    hashed_pw = generate_password_hash(data['password'])
    try:
        with get_db() as conn:
            conn.execute('INSERT INTO merchants (email, name, password) VALUES (?, ?, ?)', 
                         (data['email'], data['name'], hashed_pw))
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already exists"}), 400
    except Exception:
        return jsonify({"error": "Internal server error"}), 400
    
    return jsonify({"message": "Merchant registered successfully"}), 201

@app.route('/merchants/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) if request.is_json else request.form
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"error": "Invalid email or password"}), 401

    try:
        with get_db() as conn:
            user = conn.execute('SELECT id, password FROM merchants WHERE email = ?', (email,)).fetchone()
            
        if user and check_password_hash(user['password'], password):
            token = create_token(user['id'])
            resp = make_response(jsonify("Login successful"))
            # Secure cookie settings: HttpOnly, SameSite=Lax
            resp.set_cookie('AUTH_COOKIE', token, httponly=True, samesite='Lax')
            return resp
    except Exception:
        pass # Generic error handling to avoid leaking details
    
    return jsonify({"error": "Invalid email or password"}), 401

@app.route('/merchants/upload-wares', methods=['POST'])
def upload_wares():
    token = request.cookies.get('AUTH_COOKIE')
    user_id = verify_token(token)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    # Limit request size to prevent resource exhaustion
    if request.content_length > 1 * 1024 * 1024: # 1MB
        return jsonify({"error": "Request too large"}), 400

    data = request.get_json(silent=True) if request.is_json else request.form
    csv_content = data.get('csv')
    if not csv_content or not isinstance(csv_content, str):
        return jsonify({"error": "Invalid CSV format"}), 400

    try:
        f = io.StringIO(csv_content)
        reader = csv.reader(f)
        with get_db() as conn:
            # Limit number of rows to prevent DB exhaustion
            rows_processed = 0
            for row in reader:
                if rows_processed >= 1000:
                    break
                if len(row) == 3:
                    name, desc, price_str = row
                    try:
                        price = float(price_str)
                        conn.execute('INSERT INTO wares (merchant_id, name, description, price) VALUES (?, ?, ?, ?)', 
                                     (user_id, name, desc, price))
                        rows_processed += 1
                    except ValueError:
                        continue # Skip rows with invalid price
            conn.commit()
    except Exception:
        return jsonify({"error": "Invalid CSV format"}), 400

    return jsonify({"message": "Wares uploaded successfully"}), 200

@app.route('/wares', methods=['GET'])
def get_wares():
    try:
        min_price = request.args.get('minPrice', type=float)
        max_price = request.args.get('maxPrice', type=float)
    except (ValueError, TypeError):
        # If type conversion fails, we treat it as no filter or invalid input
        min_price = None
        max_price = None
    
    # Parameterized query prevents SQL Injection
    query = '''
        SELECT w.name, w.price, w.description, m.email as merchant_email 
        FROM wares w 
        JOIN merchants m ON w.merchant_id = m.id 
        WHERE 1=1
    '''
    params = []
    if min_price is not None:
        query += ' AND w.price >= ?'
        params.append(min_price)
    if max_price is not None:
        query += ' AND w.price <= ?'
        params.append(max_price)

    try:
        with get_db() as conn:
            wares = conn.execute(query, params).fetchall()
    except Exception:
        return "Internal Server Error", 500

    # render_template_string handles HTML escaping for variables in the template
    return render_template_string(WARES_TEMPLATE, wares=wares)

# Helper pages for the UI
@app.route('/login_page')
def login_page():
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/register_page')
def register_page():
    return render_template_string(REGISTER_TEMPLATE)

@app.route('/upload_page')
def upload_page():
    token = request.cookies.get('AUTH_COOKIE')
    if not verify_token(token):
        return "Unauthorized", 401
    return render_template_string(UPLOAD_TEMPLATE)

if __name__ == '__main__':
    # Port 5000, host 0.0.0.0 as requested
    app.run(host='0.0.0.0', port=5000)