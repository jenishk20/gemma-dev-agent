import os
import sqlite3
from flask import Flask, request, response, send_file, abort, render_template_string
from io import BytesIO

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "default_secret_key")

DB_NAME = "db.sqlite3"

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
INDEX_HTML = '''
<!DOCTYPE html>
<html>
<head><title>Profile Collection</title></head>
<body>
    <h1>Create a Profile</h1>
    <form action="/add_profile" method="post" enctype="multipart/form-data">
        <label>Username: <input type="text" name="username" required></label><br><br>
        <label>Profile HTML: <textarea name="profile_page" required></textarea></label><br><br>
        <label>Profile Photo (PNG): <input type="file" name="profile_photo" accept="image/png" required></label><br><br>
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
    username = request.form.get('username')
    profile_page = request.form.get('profile_page')
    profile_photo = request.files.get('profile_photo')

    if not username or not profile_page or not profile_photo:
        return "Invalid input", 400

    if not profile_photo.filename.lower().endswith('.png'):
        return "Invalid file format. Please upload a PNG.", 400

    photo_data = profile_photo.read()

    try:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)",
                (username, profile_page, photo_data)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        return "Profile already exists, creation forbidden", 403
    except Exception as e:
        return f"An error occurred: {str(e)}", 400

    return "Profile created successfully", 201

@app.route('/profile/<username>')
def get_profile(username):
    with get_db_connection() as conn:
        row = conn.execute("SELECT profile_page FROM profiles WHERE username = ?", (username,)).fetchone()
        if row:
            return response(row['profile_page'], mimetype='text/html')
        else:
            abort(404)

@app.route('/profile-photo/<username>')
def get_profile_photo(username):
    with get_db_connection() as conn:
        row = conn.execute("SELECT profile_photo FROM profiles WHERE username = ?", (username,)).fetchone()
        if row:
            return send_file(
                BytesIO(row['profile_photo']),
                mimetype='image/png',
                as_attachment=False,
                download_name=f"{username}.png"
            )
        else:
            abort(404)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)