import os
import sqlite3
from flask import Flask, request, send_file, abort, render_template_string
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

# Simple HTML template for the landing/upload page
INDEX_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Profile Collection</title>
    <style>
        body { font-family: sans-serif; margin: 40px; line-height: 1.6; }
        .container { max-width: 600px; margin: auto; }
        form { border: 1px solid #ccc; padding: 20px; border-radius: 8px; }
        div { margin-bottom: 15px; }
        label { display: block; font-weight: bold; }
        input, textarea { width: 100%; padding: 8px; box-sizing: border-box; }
        button { background: #007bff; color: white; border: none; padding: 10px 20px; cursor: pointer; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Create Your Profile</h1>
        <form action="/add_profile" method="post" enctype="multipart/form-data">
            <div>
                <label>Username:</label>
                <input type="text" name="username" required>
            </div>
            <div>
                <label>Profile HTML Content:</label>
                <textarea name="profile_page" rows="5" required></textarea>
            </div>
            <div>
                <label>Profile Photo (PNG):</label>
                <input type="file" name="profile_photo" accept="image/png" required>
            </div>
            <button type="submit">Create Profile</button>
        </form>
    </div>
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
        return "Invalid input: Missing required fields", 400

    # Validate file type
    if profile_photo.content_type != 'image/png':
        return "Invalid input: Profile photo must be a PNG", 400

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

@app.route('/profile/<username>', methods=['GET'])
def get_profile(username):
    with get_db_connection() as conn:
        profile = conn.execute("SELECT profile_page FROM profiles WHERE username = ?", (username,)).fetchone()
        
    if profile is None:
        abort(404)
    
    # Return the stored HTML content directly
    return render_template_string(profile['profile_page'])

@app.route('/profile-photo/<username>', methods=['GET'])
def get_profile_photo(username):
    with get_db_connection() as conn:
        profile = conn.execute("SELECT profile_photo FROM profiles WHERE username = ?", (username,)).fetchone()
        
    if profile is None:
        abort(404)
    
    return send_file(
        io.BytesIO(profile['profile_photo']),
        mimetype='image/png',
        as_attachment=False
    )

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=False)