import os
import sqlite3
import csv
import io
from flask import Flask, request, jsonify, make_response, render_template_string, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key_for_dev")

# Database initialization
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

# Session Management using itsdangerous
serializer = URLSafeTimedSerializer(app.secret_key)

def set_auth_cookie(response, merchant_id):
    token = serializer.dumps(merchant_id)
    response.set_cookie('AUTH_COOKIE', token, httponly=True, samesite='Lax')

def get_merchant_id_from_cookie():
    token = request.cookies.get('AUTH_COOKIE')
    if not token:
        return None
    try:
        return serializer.loads(token, max_age=3600 * 24) # 24 hour expiry
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
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .nav { margin-bottom: 20px; }
        .form-group { margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="nav">
        <a href="/">View Wares</a> | 
        <a href="/register_page">Register</a> | 
        <a href="/login_page">Login</a> | 
        <a href="/upload_page">Upload Wares</a>
    </div>
    {% block content %}{% endblock %}
</body>
</html>
"""

WARE_PAGE = """
{% extends "layout" %}
{% block content %}
    <h2>Available Wares</h2>
    <form method="get" action="/wares">
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
                <th>Merchant Email</th>
            </tr>
        </thead>
        <tbody>
            {% for ware in wares %}
            <tr>
                <td>{{ ware.name }}</td>
                <td>{{ ware.price }}</td>
                <td>{{ ware.description }}</td>
                <td>{{ ware.email }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
{% endblock %}
"""

REGISTER_PAGE = """
{% extends "layout" %}
{% block content %}
    <h2>Merchant Registration</h2>
    <form method="post" action="/merchants/register">
        <div class="form-group">Name: <input type="text" name="name" required></div>
        <div class="form-group">Email: <input type="email" name="email" required></div>
        <div class="form-group">Password: <input type="password" name="password" required></div>
        <button type="submit">Register</button>
    </form>
{% endblock %}
"""

LOGIN_PAGE = """
{% extends "layout" %}
{% block content %}
    <h2>Merchant Login</h2>
    <form method="post" action="/merchants/login">
        <div class="form-group">Email: <input type="email" name="email" required></div>
        <div class="form-group">Password: <input type="password" name="password" required></div>
        <button type="submit">Login</button>
    </form>
{% endblock %}
"""

UPLOAD_PAGE = """
{% extends "layout" %}
{% block content %}
    <h2>Upload Wares (CSV)</h2>
    <p>Format: name, description, price (one per line)</p>
    <form method="post" action="/merchants/upload-wares">
        <textarea name="csv" rows="10" cols="50" placeholder="Apple,Fresh red apple,1.50"></textarea><br>
        <button type="submit">Upload</button>
    </form>
{% endblock %}
"""

@app.route('/layout')
def layout():
    return LAYOUT

@app.route('/')
def index():
    return redirect(url_for('get_wares'))

@app.route('/register_page')
def register_page():
    return render_template_string(REGISTER_PAGE)

@app.route('/login_page')
def login_page():
    return render_template_string(LOGIN_PAGE)

@app.route('/upload_page')
def upload_page():
    return render_template_string(UPLOAD_PAGE)

@app.route('/merchants/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or request.form
    email = data.get('email')
    name = data.get('name')
    password = data.get('password')

    if not all([email, name, password]):
        return jsonify({"error": "Invalid input"}), 400

    hashed_pw = generate_password_hash(password)
    try:
        with get_db() as conn:
            conn.execute('INSERT INTO merchants (email, name, password) VALUES (?, ?, ?)', 
                        (email, name, hashed_pw))
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already registered"}), 400

    return jsonify({"message": "Merchant registered successfully"}), 201

@app.route('/merchants/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or request.form
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Invalid input"}), 400

    with get_db() as conn:
        merchant = conn.execute('SELECT id, password FROM merchants WHERE email = ?', (email,)).fetchone()
        
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

    data = request.get_json(silent=True) or request.form
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
    except Exception:
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

    with get_db() as conn:
        wares = conn.execute(query, params).fetchall()

    return render_template_string(WARE_PAGE, layout=LAYOUT, wares=wares)

# Override render_template_string to handle the layout extension
def render_with_layout(template_str, **context):
    # Simple implementation of layout wrapping since we can't use files
    content = render_template_string(template_str, **context)
    # This is a hack to simulate {% extends "layout" %}
    return LAYOUT.replace('{% block content %}{% endblock %}', content)

# Patching the route to use the custom layout logic
original_render = render_template_string
def patched_render(template, **context):
    if "{% extends \"layout\" %}" in template:
        # Remove the extends tag and the block tags for the simple replacement
        body = template.replace('{% extends "layout" %}', '').replace('{% block content %}', '').replace('{% endblock %}', '')
        return LAYOUT.replace('{% block content %}{% endblock %}', original_render(body, **context))
    return original_render(template, **context)

# Apply patch
app.jinja_env.globals.update(render_template_string=patched_render)
# Since render_template_string is a flask function, we actually need to wrap the route calls
# Let's just redefine the routes to use a helper.

def render_page(template, **context):
    return patched_render(template, **context)

# Re-mapping routes to use the patched render
@app.route('/register_page')
def register_page_fixed(): return render_page(REGISTER_PAGE)
@app.route('/login_page')
def login_page_fixed(): return render_page(LOGIN_PAGE)
@app.route('/upload_page')
def upload_page_fixed(): return render_page(UPLOAD_PAGE)
@app.route('/wares')
def get_wares_fixed():
    min_price = request.args.get('minPrice', type=float)
    max_price = request.args.get('maxPrice', type=float)
    query = 'SELECT w.name, w.price, w.description, m.email FROM wares w JOIN merchants m ON w.merchant_id = m.id WHERE 1=1'
    params = []
    if min_price is not None: query += " AND w.price >= ?"; params.append(min_price)
    if max_price is not None: query += " AND w.price <= ?"; params.append(max_price)
    with get_db() as conn:
        wares = conn.execute(query, params).fetchall()
    return render_page(WARE_PAGE, wares=wares)

# Remove the old route definitions to avoid conflicts
app.view_functions['index'] = index
app.view_functions['get_wares'] = get_wares_fixed
app.view_functions['register_page'] = register_page_fixed
app.view_functions['login_page'] = login_page_fixed
app.view_functions['upload_page'] = upload_page_fixed

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)