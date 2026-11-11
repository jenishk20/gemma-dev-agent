import os
import sqlite3
import aiohttp.web
from aiohttp import web

# Database setup
DB_NAME = "db.sqlite3"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                username TEXT PRIMARY KEY,
                profile_page TEXT,
                profile_photo BLOB
            )
        """)
        conn.commit()

async def handle_add_profile(request):
    try:
        data = await request.post()
        
        # Extract fields from multipart/form-data
        username = data.get('username')
        profile_page = data.get('profile_page')
        profile_photo = data.get('profile_photo')

        if not username or not profile_page or not profile_photo:
            return web.Response(text="Invalid input: missing fields", status=400)

        # aiohttp provides files as FileField objects; we need the bytes
        # If it's a FileField, read the content
        if hasattr(profile_photo, 'file'):
            photo_bytes = await profile_photo.file.read()
        else:
            # Fallback if it was sent as a string/bytes directly
            photo_bytes = profile_photo

        # Convert profile_page to string if it's bytes
        if isinstance(profile_page, bytes):
            profile_page = profile_page.decode('utf-8')

        with sqlite3.connect(DB_NAME) as conn:
            try:
                conn.execute(
                    "INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)",
                    (username, profile_page, photo_bytes)
                )
                conn.commit()
            except sqlite3.IntegrityError:
                return web.Response(text="Profile already exists", status=403)

        return web.Response(status=201)
    except Exception as e:
        return web.Response(text=str(e), status=400)

async def handle_get_profile(request):
    username = request.match_info.get('username')
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute("SELECT profile_page FROM profiles WHERE username = ?", (username,))
        row = cursor.fetchone()
        
    if row:
        return web.Response(text=row[0], content_type='text/html')
    else:
        return web.Response(text="Profile not found", status=404)

async def handle_get_photo(request):
    username = request.match_info.get('username')
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute("SELECT profile_photo FROM profiles WHERE username = ?", (username,))
        row = cursor.fetchone()
        
    if row:
        return web.Response(body=row[0], content_type='image/png')
    else:
        return web.Response(text="Photo not found", status=404)

def main():
    init_db()
    app = web.Application()
    
    app.add_routes([
        web.post('/add_profile', handle_add_profile),
        web.get('/profile/{username}', handle_get_profile),
        web.get('/profile-photo/{username}', handle_get_photo),
    ])
    
    web.run_app(app, host='0.0.0.0', port=5000)

if __name__ == "__main__":
    main()