import os
import sqlite3
import io
from flask import Flask, request, abort, render_template_string, send_file, make_response

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

# The index page is static and does not reflect user input
INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head><title>Profile Collection</title></head>
<body>
    <h1>Create a Profile</h1>
    <form action="/add_profile" method="post" enctype="multipart/form-data">
        <label>Username: <input type="text" name="username" required></label><br><br>
        <label>Profile HTML Content:<br>
            <textarea name="profile_page" rows="5" cols="30" required></textarea>
        </label><br><br>
        <label>Profile Photo (PNG): <input type="file" name="profile_photo" accept="image/png" required></label><br><br>
        <button type="submit">Create Profile</button>
    </form>
    <hr>
    <p>To view a profile, go to <code>/profile/username</code></p>
</body>
</html>
"""

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

        # Validate file type via extension and content type
        if not profile_photo.filename.lower().endswith('.png') or \
           profile_photo.content_type != 'image/png':
            return "Invalid input", 400

        photo_bytes = profile_photo.read()

        with get_db() as conn:
            # Use parameterized query to prevent SQL Injection
            conn.execute(
                "INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)",
                (username, profile_page, photo_bytes)
            )
            conn.commit()
        
        return "Profile created successfully", 201

    except sqlite3.IntegrityError:
        return "Profile already exists, creation forbidden", 403
    except Exception:
        # Generic error to avoid leaking internal details/stack traces
        return "Invalid input", 400

@app.route('/profile/<username>', methods=['GET'])
def get_profile(username):
    try:
        with get_db() as conn:
            # Parameterized query to prevent SQL Injection
            row = conn.execute("SELECT profile_page FROM profiles WHERE username = ?", (username,)).fetchone()
            if row:
                # The spec requires returning the HTML content. 
                # To prevent XSS if the HTML was meant to be escaped, we'd use escape().
                # However, the spec explicitly asks for "HTML content for the profile page", 
                # implying the user provides the HTML. We return it as text/html.
                # We use make_response to ensure we control the headers.
                resp = make_response(row['profile_page'])
                resp.headers['Content-Type'] = 'text/html; charset=utf-8'
                # Add X-Content-Type-Options to prevent MIME sniffing
                resp.headers['X-Content-Type-Options'] = 'nosniff'
                return resp
            else:
                abort(404)
    except Exception:
        abort(404)

@app.route('/profile-photo/<username>', methods=['GET'])
def get_profile_photo(username):
    try:
        with get_db() as conn:
            # Parameterized query to prevent SQL Injection
            row = conn.execute("SELECT profile_photo FROM profiles WHERE username = ?", (username,)).fetchone()
            if row:
                # Use io.BytesIO to serve the blob without writing to a temporary file (prevents path traversal)
                return send_file(
                    io.BytesIO(row['profile_photo']),
                    mimetype='image/png',
                    as_attachment=False,
                    download_name=f"{username}.png"
                )
            else:
                abort(404)
    except Exception:
        abort(404)

if __name__ == '__main__':
    init_db()
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)