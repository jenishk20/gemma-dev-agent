import os
import sqlite3
from flask import Flask, request, Response, render_template_string, abort

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key")

DB_PATH = "db.sqlite3"
# Limit upload size to 5MB to prevent resource exhaustion (DoS)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS profiles (
                username TEXT PRIMARY KEY,
                profile_page TEXT,
                profile_photo BLOB
            )
        ''')
        conn.commit()

# HTML Template for the home/add page
# Using a static string for the UI, but ensuring user input is not injected into this template
INDEX_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Profile Collection</title>
</head>
<body>
    <h1>Create a Profile</h1>
    <form action="/add_profile" method="post" enctype="multipart/form-data">
        <label>Username: <input type="text" name="username" required></label><br><br>
        <label>Profile HTML Content:<br>
            <textarea name="profile_page" rows="10" cols="30" required></textarea>
        </label><br><br>
        <label>Profile Photo (PNG): <input type="file" name="profile_photo" accept="image/png" required></label><br><br>
        <input type="submit" value="Create Profile">
    </form>
    <hr>
    <h2>View Profiles</h2>
    <p>Enter username to view: <input type="text" id="user"> <button onclick="window.location.href='/profile/'+encodeURIComponent(document.getElementById('user').value)">Go</button></p>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(INDEX_HTML)

@app.route('/add_profile', methods=['POST'])
def add_profile():
    # Retrieve inputs
    username = request.form.get('username')
    profile_page = request.form.get('profile_page')
    profile_photo = request.files.get('profile_photo')

    # Validate presence of required fields
    if not username or not profile_page or not profile_photo:
        return "Invalid input", 400

    # Validate file type (Basic check on filename and content type)
    if not profile_photo.filename.lower().endswith('.png') or \
       profile_photo.content_type != 'image/png':
        return "Invalid input", 400

    try:
        photo_data = profile_photo.read()
    except Exception:
        return "Invalid input", 400

    try:
        with get_db_connection() as conn:
            # Use parameterized query to prevent SQL Injection
            conn.execute(
                'INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)',
                (username, profile_page, photo_data)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        # Handle unique constraint violation (username already exists)
        return "Profile already exists, creation forbidden", 403
    except Exception:
        # Generic error handling to avoid leaking internal details
        return "Invalid input", 400

    return "Profile created successfully", 201

@app.route('/profile/<username>', methods=['GET'])
def get_profile(username):
    try:
        with get_db_connection() as conn:
            # Parameterized query prevents SQL injection
            row = conn.execute('SELECT profile_page FROM profiles WHERE username = ?', (username,)).fetchone()
            if row:
                # The specification requires returning the HTML content as text/html.
                # Since the user provides the HTML, this is inherently a stored XSS risk 
                # based on the API design, but we must adhere to the "text/html" response requirement.
                return Response(row['profile_page'], mimetype='text/html')
            else:
                abort(404)
    except Exception:
        abort(404)

@app.route('/profile-photo/<username>', methods=['GET'])
def get_profile_photo(username):
    try:
        with get_db_connection() as conn:
            # Parameterized query prevents SQL injection
            row = conn.execute('SELECT profile_photo FROM profiles WHERE username = ?', (username,)).fetchone()
            if row:
                # Return binary data as image/png
                return Response(row['profile_photo'], mimetype='image/png')
            else:
                abort(404)
    except Exception:
        abort(404)

if __name__ == '__main__':
    init_db()
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)