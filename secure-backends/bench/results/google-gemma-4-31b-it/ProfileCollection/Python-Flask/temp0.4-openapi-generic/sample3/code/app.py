import os
import sqlite3
from flask import Flask, request, response, send_file, abort, render_template_string
from werkzeug.utils import secure_filename
import io

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key_for_dev")

DB_PATH = "db.sqlite3"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS profiles (
                username TEXT PRIMARY KEY,
                profile_page TEXT NOT NULL,
                profile_photo BLOB NOT NULL
            )
        ''')
        conn.commit()

# Simple HTML template for the home/upload page
INDEX_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>Profile Collection</title></head>
<body>
    <h1>Create Your Profile</h1>
    <form action="/add_profile" method="post" enctype="multipart/form-data">
        <label>Username: <input type="text" name="username" required></label><br><br>
        <label>Profile HTML: <textarea name="profile_page" required></textarea></label><br><br>
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
    return render_template_string(INDEX_TEMPLATE)

@app.route('/add_profile', methods=['POST'])
def add_profile():
    username = request.form.get('username')
    profile_page = request.form.get('profile_page')
    profile_photo = request.files.get('profile_photo')

    if not username or not profile_page or not profile_photo:
        return "Invalid input: Missing fields", 400

    if not profile_photo.filename.lower().endswith('.png'):
        return "Invalid input: Photo must be a PNG", 400

    # Read photo bytes
    photo_bytes = profile_photo.read()

    try:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)",
                (username, profile_page, photo_bytes)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        return "Profile already exists, creation forbidden", 403
    except Exception as e:
        return f"Internal Server Error: {str(e)}", 500

    return "Profile created successfully", 201

@app.route('/profile/<username>')
def get_profile(username):
    with get_db_connection() as conn:
        user = conn.execute("SELECT profile_page FROM profiles WHERE username = ?", (username,)).fetchone()
    
    if user is None:
        abort(404)
    
    # Returning the HTML content as specified in the OpenAPI schema
    # Note: In a real production app, we would sanitize this HTML to prevent XSS.
    return response.make_response(user['profile_page'], 200, {'Content-Type': 'text/html'})

@app.route('/profile-photo/<username>')
def get_profile_photo(username):
    with get_db_connection() as conn:
        user = conn.execute("SELECT profile_photo FROM profiles WHERE username = ?", (username,)).fetchone()
    
    if user is None:
        abort(404)
    
    return send_file(
        io.BytesIO(user['profile_photo']),
        mimetype='image/png',
        as_attachment=False
    )

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)