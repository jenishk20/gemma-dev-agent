import os
import sqlite3
from flask import Flask, request, response, send_file, abort, render_template_string
from io import BytesIO

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key")

DB_NAME = "db.sqlite3"
# Limit upload size to 5MB to prevent resource exhaustion
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
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

# Simple HTML template for the home/add page
# Using a static string, no user input is passed to render_template_string here
INDEX_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Profile Collection</title></head>
<body style="font-family: sans-serif; margin: 20px;">
    <h1>Create a Profile</h1>
    <form action="/add_profile" method="post" enctype="multipart/form-data">
        <div><label>Username: <input type="text" name="username" required></label></div><br>
        <div><label>Profile HTML: <textarea name="profile_page" rows="10" cols="30" required></textarea></label></div><br>
        <div><label>Profile Photo (PNG): <input type="file" name="profile_photo" accept="image/png" required></label></div><br>
        <input type="submit" value="Create Profile">
    </form>
    <hr>
    <p>To view a profile, go to <code>/profile/username</code></p>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(INDEX_HTML)

@app.route('/add_profile', methods=['POST'])
def add_profile():
    try:
        username = request.form.get('username')
        profile_page = request.form.get('profile_page')
        profile_photo = request.files.get('profile_photo')

        if not username or not profile_page or not profile_photo:
            return "Invalid input", 400

        # Validate file type by content if possible, but here we check extension and basic header
        # as per the OpenAPI requirement for PNG.
        photo_data = profile_photo.read()
        if not photo_data.startswith(b'\x89PNG\r\n\x1a\n'):
            return "Invalid input", 400

        # Use parameterized query to prevent SQL Injection
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)",
                (username, profile_page, photo_data)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        return "Profile already exists, creation forbidden", 403
    except Exception:
        # Generic error to avoid leaking internal details
        return "Invalid input", 400

    return "Profile created successfully", 201

@app.route('/profile/<username>')
def get_profile(username):
    try:
        with get_db_connection() as conn:
            # Parameterized query prevents SQLi
            row = conn.execute("SELECT profile_page FROM profiles WHERE username = ?", (username,)).fetchone()
            if row:
                # The spec requires returning the HTML content provided by the user.
                # To prevent XSS on the viewer's side, normally we'd escape, 
                # but the spec explicitly says "Retrieves the HTML content", 
                # implying the user-provided HTML is the intended response.
                return response(row['profile_page'], mimetype='text/html')
            else:
                abort(404)
    except Exception:
        abort(404)

@app.route('/profile-photo/<username>')
def get_profile_photo(username):
    try:
        with get_db_connection() as conn:
            # Parameterized query prevents SQLi
            row = conn.execute("SELECT profile_photo FROM profiles WHERE username = ?", (username,)).fetchone()
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