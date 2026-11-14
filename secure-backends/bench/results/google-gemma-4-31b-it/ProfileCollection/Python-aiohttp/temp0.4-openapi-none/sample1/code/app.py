import os
import sqlite3
import aiohttp.web
from aiohttp import web

# Database setup
DB_PATH = "db.sqlite3"

def init_db():
    conn = sqlite3.connect(DB_PATH)
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

def db_query(query, params=(), fetchone=False, commit=False):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(query, params)
    if commit:
        conn.commit()
        res = None
    elif fetchone:
        res = cursor.fetchone()
    else:
        res = cursor.fetchall()
    conn.close()
    return res

async def add_profile(request):
    try:
        data = await request.post()
        username = data.get('username')
        profile_page = data.get('profile_page')
        profile_photo = data.get('profile_photo')

        if not username or not profile_page or not profile_photo:
            return web.Response(text="Invalid input", status=400)

        # aiohttp FileStorage objects are passed for files
        # We need the actual bytes
        if hasattr(profile_photo, 'read'):
            photo_bytes = await profile_photo.read()
        else:
            photo_bytes = profile_photo

        # Check if user exists
        exists = db_query("SELECT 1 FROM profiles WHERE username = ?", (username,), fetchone=True)
        if exists:
            return web.Response(text="Profile already exists", status=403)

        db_query("INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)", 
                 (username, profile_page, photo_bytes), commit=True)
        
        return web.Response(status=201)
    except Exception as e:
        return web.Response(text=str(e), status=400)

async def get_profile(request):
    username = request.match_info.get('username')
    row = db_query("SELECT profile_page FROM profiles WHERE username = ?", (username,), fetchone=True)
    
    if row:
        return web.Response(text=row[0], content_type='text/html')
    return web.Response(text="Profile not found", status=404)

async def get_profile_photo(request):
    username = request.match_info.get('username')
    row = db_query("SELECT profile_photo FROM profiles WHERE username = ?", (username,), fetchone=True)
    
    if row:
        return web.Response(body=row[0], content_type='image/png')
    return web.Response(text="Profile photo not found", status=404)

async def init_app():
    app = web.Application()
    app.add_routes([
        web.post('/add_profile', add_profile),
        web.get('/profile/{username}', get_profile),
        web.get('/profile-photo/{username}', get_profile_photo),
    ])
    return app

if __name__ == '__main__':
    init_db()
    app = None # Placeholder for global scope if needed
    web.run_app(init_app(), host='0.0.0.0', port=5000)