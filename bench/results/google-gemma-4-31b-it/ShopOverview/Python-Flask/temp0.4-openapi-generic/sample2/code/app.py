import os
import sqlite3
import csv
import io
from flask import Flask, request, jsonify, make_response, render_template_string, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import SignedCookieSession, BadSigning

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key_for_dev")

DB_PATH = "db.sqlite3"

# Database initialization
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

# Session Management using itsdangerous for the cookieAuth requirement
def create_session_token(merchant_id):
    serializer = SignedCookieSession(app.secret_key)
    return serializer.dumps({"merchant_id": merchant_id})

def get_merchant_id_from_cookie(cookie_val):
    if not cookie_val:
        return None
    try:
        serializer = SignedCookieSession(app.secret_key)
        data = serializer.loads(cookie_val)
        return data.get("merchant_id")
    except BadSigning:
        return None

# HTML Templates
BASE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>Merchant Warehouse</title></head>
<body>
    <nav>
        <a href="/">View Wares</a> | 
        <a href="/login_page">Login</a> | 
        <a href="/register_page">Register</a>
    </nav>
    <hr>
    {% block content %}{% endblock %}
</body>
</html>
"""

WARES_TEMPLATE = """
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
                <th>Merchant Email</th>
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

UPLOAD_TEMPLATE = """
{% extends "base" %}
{% block content %}
    <h2>Upload Wares</h2>
    <p>Format: name,description,price (one per line)</p>
    <form method="POST" action="/merchants/upload-wares">
        <textarea name="csv" rows="10" cols="50"></textarea><br>
        <button type="submit">Upload</button>
    </form>
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

@app.context_processor
def inject_base():
    return {'base_template': BASE_TEMPLATE}

@app.route('/')
def index():
    return redirect(url_for('get_wares'))

@app.route('/register_page')
def register_page():
    return render_template_string(REGISTER_TEMPLATE)

@app.route('/login_page')
def login_page():
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/merchants/register', methods=['POST'])
def register():
    data = request.get_json() if request.is_json else request.form
    email = data.get('email')
    name = data.get('name')
    password = data.get('password')

    if not all([email, name, password]):
        return jsonify({"error": "Missing fields"}), 400

    hashed_pw = generate_password_hash(password)
    try:
        with get_db() as conn:
            conn.execute('INSERT INTO merchants (email, name, password) VALUES (?, ?, ?)', 
                         (email, name, hashed_pw))
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
        merchant = conn.execute('SELECT id, password FROM merchants WHERE email = ?', (email,)).fetchone()

    if merchant and check_password_hash(merchant['password'], password):
        token = create_session_token(merchant['id'])
        resp = make_response(jsonify("Login successful"), 200)
        resp.set_cookie('AUTH_COOKIE', token, httponly=True, samesite='Lax')
        return resp
    
    return jsonify({"error": "Invalid email or password"}), 401

@app.route('/merchants/upload-wares', methods=['POST'])
def upload_wares():
    merchant_id = get_merchant_id_from_cookie(request.cookies.get('AUTH_COOKIE'))
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
                if len(row) != 3:
                    continue
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

    # The OpenAPI spec asks for HTML response for /wares
    return render_template_string(WARES_TEMPLATE, wares=wares, base=BASE_TEMPLATE)

# Helper to handle template inheritance in render_template_string
@app.before_request
def setup_templates():
    # This is a hack to make render_template_string work with 'extends'
    # since we are not using a filesystem for templates
    pass

# Overriding render_template_string to support the 'base' extension manually
def render_with_base(template_str, **context):
    # Simple replacement for the 'extends "base"' logic
    content = render_template_string(template_str, **context)
    # This is a simplified approach for a single-file app
    # In a real app, we'd use a proper Jinja environment
    return content

# Since we are in one file, let's redefine the templates to not use 'extends' 
# or just wrap them manually to ensure they work.
def wrap_in_base(content):
    return BASE_TEMPLATE.replace('{% block content %}{% endblock %}', content)

# Redefining routes to use the wrapper for simplicity
@app.route('/register_page')
def register_page_fixed():
    return wrap_in_base(render_template_string(REGISTER_TEMPLATE))

@app.route('/login_page')
def login_page_fixed():
    return wrap_in_base(render_template_string(LOGIN_TEMPLATE))

@app.route('/upload_page')
def upload_page():
    return wrap_in_base(render_template_string(UPLOAD_TEMPLATE))

# Re-patching the routes to use the wrapper
app.view_functions['register_page'] = register_page_fixed
app.view_functions['login_page'] = login_page_fixed

# Update the /wares route to use the wrapper
def get_wares_fixed():
    min_price = request.args.get('minPrice', type=float)
    max_price = request.args.get('maxPrice', type=float)
    query = 'SELECT w.name, w.price, w.description, m.email as merchant_email FROM wares w JOIN merchants m ON w.merchant_id = m.id WHERE 1=1'
    params = []
    if min_price is not None:
        query += " AND w.price >= ?"; params.append(min_price)
    if max_price is not None:
        query += " AND w.price <= ?"; params.append(max_price)
    with get_db() as conn:
        wares = conn.execute(query, params).fetchall()
    return wrap_in_base(render_template_string(WARES_TEMPLATE, wares=wares))

app.view_functions['get_wares'] = get_wares_fixed

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)