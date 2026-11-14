import os
import sqlite3
import csv
import io
from flask import Flask, request, jsonify, make_response, render_template_string, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

app = Flask(__name__)
# Use the provided APP_SECRET or a strong fallback
app.secret_key = os.environ.get("APP_SECRET", os.urandom(32))

# Database setup
DB_PATH = "db.sqlite3"

def get_db():
    # Using check_same_thread=False is not needed here as Flask handles requests in threads
    # and we open/close connections per request.
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

# Authentication helper
serializer = URLSafeTimedSerializer(app.secret_key)

def get_user_id_from_cookie():
    token = request.cookies.get("AUTH_COOKIE")
    if not token:
        return None
    try:
        # max_age ensures the token expires after 24 hours
        user_id = serializer.loads(token, max_age=3600 * 24)
        return int(user_id)
    except (BadSignature, SignatureExpired, ValueError, TypeError):
        return None

# HTML Templates - Using Jinja2's auto-escaping (default in render_template_string)
# to prevent XSS.
BASE_LAYOUT = """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Warehouse</title></head>
<body>
    <nav>
        <a href="{{ url_for('get_wares') }}">View Wares</a> | 
        <a href="{{ url_for('register_page') }}">Register</a> | 
        <a href="{{ url_for('login_page') }}">Login</a>
    </nav>
    <hr>
    {% block content %}{% endblock %}
</body>
</html>
"""

WARE_PAGE_TEMPLATE = BASE_LAYOUT + """
{% block content %}
    <h1>Available Wares</h1>
    <form method="GET" action="{{ url_for('get_wares') }}">
        Min Price: <input type="number" step="0.01" name="minPrice">
        Max Price: <input type="number" step="0.01" name="maxPrice">
        <button type="submit">Filter</button>
    </form>
    <table border="1">
        <thead>
            <tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr>
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

LOGIN_PAGE_TEMPLATE = BASE_LAYOUT + """
{% block content %}
    <h1>Merchant Login</h1>
    <form method="POST" action="{{ url_for('login') }}">
        Email: <input type="email" name="email" required><br>
        Password: <input type="password" name="password" required><br>
        <button type="submit">Login</button>
    </form>
{% endblock %}
"""

REGISTER_PAGE_TEMPLATE = BASE_LAYOUT + """
{% block content %}
    <h1>Merchant Registration</h1>
    <form method="POST" action="{{ url_for('register') }}">
        Name: <input type="text" name="name" required><br>
        Email: <input type="email" name="email" required><br>
        Password: <input type="password" name="password" required><br>
        <button type="submit">Register</button>
    </form>
{% endblock %}
"""

UPLOAD_PAGE_TEMPLATE = BASE_LAYOUT + """
{% block content %}
    <h1>Upload Wares</h1>
    <p>Format: name,description,price (one per line)</p>
    <form method="POST" action="{{ url_for('upload_wares') }}">
        <textarea name="csv" rows="10" cols="50"></textarea><br>
        <button type="submit">Upload</button>
    </form>
{% endblock %}
"""

# API Routes
@app.route('/merchants/register', methods=['POST'])
def register():
    # Limit request size to prevent resource exhaustion
    if request.content_length > 10 * 1024: 
        return jsonify({"error": "Request too large"}), 400

    if request.is_json:
        data = request.get_json()
    else:
        # Support form submission for the register_page
        data = request.form

    if not data or not all(k in data for k in ('email', 'name', 'password')):
        return jsonify({"error": "Invalid input"}), 400
    
    # Password hashing using Werkzeug (PBKDF2 by default)
    hashed_pw = generate_password_hash(data['password'])
    try:
        with get_db() as conn:
            # Parameterized query to prevent SQL Injection
            conn.execute('INSERT INTO merchants (email, name, password) VALUES (?, ?, ?)', 
                        (data['email'], data['name'], hashed_pw))
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already registered"}), 400
    except Exception:
        return jsonify({"error": "Internal server error"}), 400
    
    return jsonify({"message": "Merchant registered successfully"}), 201

@app.route('/merchants/login', methods=['POST'])
def login():
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form

    if not data:
        return jsonify({"error": "Invalid input"}), 400

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Invalid email or password"}), 401

    try:
        with get_db() as conn:
            user = conn.execute('SELECT id, password FROM merchants WHERE email = ?', (email,)).fetchone()
        
        if user and check_password_hash(user['password'], password):
            token = serializer.dumps(str(user['id']))
            # Use redirect for HTML forms, JSON for API calls
            if request.is_json:
                resp = make_response(jsonify("Login successful"))
            else:
                resp = make_response(redirect(url_for('upload_page')))
            
            # Set cookie with security flags
            resp.set_cookie("AUTH_COOKIE", token, httponly=True, samesite='Lax')
            return resp
    except Exception:
        return jsonify({"error": "Internal server error"}), 401
    
    return jsonify({"error": "Invalid email or password"}), 401

@app.route('/merchants/upload-wares', methods=['POST'])
def upload_wares():
    user_id = get_user_id_from_cookie()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    # Resource exhaustion: limit CSV size
    if request.content_length > 1 * 1024 * 1024: # 1MB limit
        return jsonify({"error": "Request too large"}), 400

    if request.is_json:
        data = request.get_json()
        csv_content = data.get('csv', '')
    else:
        csv_content = request.form.get('csv', '')

    if not csv_content:
        return jsonify({"message": "No data to upload"}), 200

    try:
        f = io.StringIO(csv_content)
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
                conn.execute('INSERT INTO wares (merchant_id, name, description, price) VALUES (?, ?, ?, ?)', 
                            (user_id, name, desc, price))
            conn.commit()
    except Exception:
        return jsonify({"error": "Internal server error"}), 400

    if request.is_json:
        return jsonify({"message": "Wares uploaded successfully"}), 200
    return redirect(url_for('get_wares'))

@app.route('/wares', methods=['GET'])
def get_wares():
    try:
        min_price = request.args.get('minPrice', type=float)
        max_price = request.args.get('maxPrice', type=float)
        
        query = '''
            SELECT w.name, w.price, w.description, m.email as merchant_email 
            FROM wares w JOIN merchants m ON w.merchant_id = m.id 
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
        
        # render_template_string automatically escapes variables passed to the template
        return render_template_string(WARE_PAGE_TEMPLATE, wares=wares)
    except Exception:
        return "Internal Server Error", 500

# Web Pages
@app.route('/register_page')
def register_page():
    return render_template_string(REGISTER_PAGE_TEMPLATE)

@app.route('/login_page')
def login_page():
    return render_template_string(LOGIN_PAGE_TEMPLATE)

@app.route('/upload_page')
def upload_page():
    if not get_user_id_from_cookie():
        return redirect(url_for('login_page'))
    return render_template_string(UPLOAD_PAGE_TEMPLATE)

if __name__ == '__main__':
    init_db()
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)