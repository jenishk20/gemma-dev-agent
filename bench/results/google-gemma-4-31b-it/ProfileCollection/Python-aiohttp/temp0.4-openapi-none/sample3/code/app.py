import os
import sqlite3
from aiohttp import web

# Database initialization
DB_NAME = "db.sqlite3"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            username TEXT PRIMARY KEY,
            profile_page TEXT,
            profile_photo BLOB
        )
    ''')
    conn.commit()
    conn.close()

async def add_profile(request):
    try:
        # aiohttp handles multipart/form-data via request.post()
        data = await request.post()
        
        username = data.get('username')
        profile_page = data.get('profile_page')
        profile_photo = data.get('profile_photo')

        if not username or not profile_page or not profile_photo:
            return web.Response(text="Invalid input: missing fields", status=400)

        # Extract content from FileStorage objects if necessary
        # aiohttp's data.get() for files returns a FileStorage object
        # We need the actual bytes/string
        
        # Handle the case where fields might be uploaded as files or text
        # For simplicity in this implementation, we assume standard form fields 
        # or file uploads handled by aiohttp
        
        # Extracting values from FileStorage objects
        p_page_content = profile_page
        if hasattr(profile_page, 'read'):
            p_page_content = await profile_page.read()
            if isinstance(p_page_content, bytes):
                p_page_content = p_page_content.decode('utf-8')

        p_photo_content = profile_photo
        if hasattr(profile_photo, 'read'):
            p_photo_content = await profile_photo.read()

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)', 
                           (username, p_page_content, p_photo_content))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return web.Response(text="Profile already exists", status=403)
        
        conn.close()
        return web.Response(status=201)
    except Exception as e:
        return web.Response(text=str(e), status=400)

async def get_profile(request):
    username = request.match_info.get('username')
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT profile_page FROM profiles WHERE username = ?', (username,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return web.Response(text=row[0], content_type='text/html')
    else:
        return web.Response(status=404)

async def get_profile_photo(request):
    username = request.match_info.get('username')
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT profile_photo FROM profiles WHERE username = ?', (username,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return web.Response(body=row[0], content_type='image/png')
    else:
        return web.Response(status=404)

async def app_main():
    init_db()
    app = web.Application()
    app.add_routes([
        web.post('/add_profile', add_profile),
        web.get('/profile/{username}', get_profile),
        web.get('/profile-photo/{username}', get_profile_photo),
    ])
    return app

if __name__ == '__main__':
    web.run_app(app_main(), port=5000, address='0.0.0.0')