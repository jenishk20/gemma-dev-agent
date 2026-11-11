import os
import sqlite3
from flask import Flask, request, send_file, abort, render_template_string
from io import BytesIO

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key")

DB_NAME = "db.sqlite3"
# Limit upload size to 5MB to prevent resource exhaustion
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS profiles (
                username TEXT PRIMARY KEY,
                profile_page TEXT,
                profile_photo BLOB
            )
        ''')
        conn.commit()

# Static HTML for the home page to avoid template injection
INDEX_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Profile Collection</title></head>
<body style="font-family: sans-serif;">
    <h1>Create a Profile</h1>
    <form action="/add_profile" method="post" enctype="multipart/form-data">
        <label>Username: <input type="text" name="username" required></label><br><br>
        <label>Profile HTML: <textarea name="profile_page" rows="10" cols="30" required></textarea></label><br><br>
        <label>Profile Photo (PNG): <input type="file" name="profile_photo" accept="image/png" required></label><br><br>
        <input type="submit" value="Create Profile">
    </form>
    <hr>
    <h2>Existing Profiles</h2>
    <p>Use <code>/profile/&lt;username&gt;</code> to view a profile.</p>
</body>
</html>
'''

@app.route('/')
def index():
    # Use render_template_string with a static string to avoid any dynamic evaluation
    return render_template_string(INDEX_HTML)

@app.route('/add_profile', methods=['POST'])
def add_profile():
    try:
        username = request.form.get('username')
        profile_page = request.form.get('profile_page')
        profile_photo = request.files.get('profile_photo')

        if not username or not profile_page or not profile_photo:
            return "Invalid input", 400

        # Basic validation for PNG (checking extension and magic bytes)
        if not profile_photo.filename.lower().endswith('.png'):
            return "Invalid input", 400
        
        photo_data = profile_photo.read()
        if not photo_data.startswith(b'\x89PNG\r\n\x1a\n'):
            return "Invalid input", 400

        # Parameterized query prevents SQL Injection
        with get_db() as conn:
            conn.execute(
                'INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)',
                (username, profile_page, photo_data)
            )
            conn.commit()
        
        return "Profile created successfully", 201

    except sqlite3.IntegrityError:
        return "Profile already exists, creation forbidden", 403
    except Exception:
        # Generic error to avoid leaking internal stack traces
        return "Invalid input", 400

@app.route('/profile/<username>', methods=['GET'])
def get_profile(username):
    try:
        with get_db() as conn:
            # Parameterized query prevents SQL Injection
            row = conn.execute('SELECT profile_page FROM profiles WHERE username = ?', (username,)).fetchone()
            if row:
                # The spec requires returning the HTML content as text/html.
                # Since the user provides the HTML, this is a stored XSS risk by design of the API.
                # However, we ensure the response is treated as HTML and not a template.
                return row['profile_page'], 200, {'Content-Type': 'text/html; charset=utf-8'}
            else:
                abort(404)
    except Exception:
        abort(404)

@app.route('/profile-photo/<username>', methods=['GET'])
def get_profile_photo(username):
    try:
        with get_db() as conn:
            # Parameterized query prevents SQL Injection
            row = conn.execute('SELECT profile_photo FROM profiles WHERE username = ?', (username,)).fetchone()
            if row:
                return send_file(
                    BytesIO(row['profile_photo']),
                    mimetype='image/png'
                )
            else:
                abort(404)
    except Exception:
        abort(404)

if __name__ == '__main__':
    init_db()
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)