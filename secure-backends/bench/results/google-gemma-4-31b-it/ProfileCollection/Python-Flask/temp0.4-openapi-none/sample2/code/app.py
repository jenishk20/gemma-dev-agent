import os
import sqlite3
from flask import Flask, request, response, abort, render_template_string
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key")

DB_PATH = "db.sqlite3"

def get_db():
    conn = sqlite3.connect(DB_PATH)
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

@app.route('/add_profile', methods=['POST'])
def add_profile():
    # The OpenAPI schema specifies multipart/form-data
    username = request.form.get('username')
    profile_page = request.form.get('profile_page')
    profile_photo = request.files.get('profile_photo')

    if not username or not profile_page or not profile_photo:
        return "Invalid input: missing fields", 400

    # Basic validation for PNG (checking magic bytes)
    photo_data = profile_photo.read()
    if not photo_data.startswith(b'\x89PNG\r\n\x1a\n'):
        return "Invalid input: profile_photo must be a PNG", 400

    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)",
                (username, profile_page, photo_data)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        return "Profile already exists, creation forbidden", 403

    return "Profile created successfully", 201

@app.route('/profile/<username>', methods=['GET'])
def get_profile(username):
    with get_db() as conn:
        row = conn.execute("SELECT profile_page FROM profiles WHERE username = ?", (username,)).fetchone()
        if row:
            return response(row['profile_page'], mimetype='text/html')
        else:
            abort(404)

@app.route('/profile-photo/<username>', methods=['GET'])
def get_profile_photo(username):
    with get_db() as conn:
        row = conn.execute("SELECT profile_photo FROM profiles WHERE username = ?", (username,)).fetchone()
        if row:
            return response(row['profile_photo'], mimetype='image/png')
        else:
            abort(404)

# Simple landing page for convenience to test the app
@app.route('/')
def index():
    return render_template_string('''
        <h1>Profile Collection</h1>
        <form action="/add_profile" method="post" enctype="multipart/form-data">
            Username: <input type="text" name="username"><br>
            Profile HTML: <textarea name="profile_page"></textarea><br>
            Profile Photo (PNG): <input type="file" name="profile_photo"><br>
            <input type="submit" value="Create Profile">
        </form>
    ''')

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)