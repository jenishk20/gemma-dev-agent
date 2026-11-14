import os
import sqlite3
from flask import Flask, request, response, abort, render_template_string

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key")

# Resource exhaustion: Limit the maximum request body size (e.g., 16MB)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

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
    try:
        # The OpenAPI schema specifies multipart/form-data
        username = request.form.get('username')
        profile_page = request.form.get('profile_page')
        profile_photo = request.files.get('profile_photo')

        if not username or not profile_page or not profile_photo:
            return "Invalid input", 400

        # Resource exhaustion: Limit username length to prevent DB/Memory abuse
        if len(username) > 255:
            return "Invalid input", 400

        # Validate PNG (checking magic bytes)
        photo_data = profile_photo.read()
        if not photo_data.startswith(b'\x89PNG\r\n\x1a\n'):
            return "Invalid input", 400

        with get_db() as conn:
            # SQL Injection prevention: Using parameterized queries
            conn.execute(
                "INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)",
                (username, profile_page, photo_data)
            )
            conn.commit()
            
    except sqlite3.IntegrityError:
        return "Profile already exists, creation forbidden", 403
    except Exception:
        # Error handling: Generic error to avoid leaking internal details
        return "Invalid input", 400

    return "Profile created successfully", 201

@app.route('/profile/<username>', methods=['GET'])
def get_profile(username):
    try:
        # Resource exhaustion: Limit input length
        if len(username) > 255:
            abort(404)

        with get_db() as conn:
            # SQL Injection prevention: Using parameterized queries
            row = conn.execute("SELECT profile_page FROM profiles WHERE username = ?", (username,)).fetchone()
            if row:
                # The specification requires returning the HTML content as provided.
                # Since the API is designed to serve user-provided HTML, we return it as is.
                # Note: In a real-world app, this is a stored XSS risk, but the OpenAPI 
                # spec explicitly defines the response as text/html based on user input.
                return response(row['profile_page'], mimetype='text/html')
            else:
                abort(404)
    except Exception:
        abort(404)

@app.route('/profile-photo/<username>', methods=['GET'])
def get_profile_photo(username):
    try:
        if len(username) > 255:
            abort(404)

        with get_db() as conn:
            # SQL Injection prevention: Using parameterized queries
            row = conn.execute("SELECT profile_photo FROM profiles WHERE username = ?", (username,)).fetchone()
            if row:
                return response(row['profile_photo'], mimetype='image/png')
            else:
                abort(404)
    except Exception:
        abort(404)

@app.route('/')
def index():
    # Using render_template_string with a static string is safe here as no user input is passed to it.
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
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)