import os
import sqlite3
import aiohttp
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

async def add_profile(request):
    try:
        data = await request.post()
        username = data.get('username')
        profile_page = data.get('profile_page')
        profile_photo = data.get('profile_photo')

        if not username or not profile_page or not profile_photo:
            return web.Response(text="Invalid input: missing fields", status=400)

        # Handle multipart file upload for profile_photo
        # aiohttp provides the file as a FileUpload object
        photo_content = await profile_photo.read()

        try:
            with sqlite3.connect(DB_NAME) as conn:
                conn.execute(
                    "INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)",
                    (username, profile_page, photo_content)
                )
                conn.commit()
        except sqlite3.IntegrityError:
            return web.Response(text="Profile already exists", status=403)

        return web.Response(status=201)
    except Exception as e:
        return web.Response(text=str(e), status=400)

async def get_profile(request):
    username = request.match_info.get('username')
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute("SELECT profile_page FROM profiles WHERE username = ?", (username,))
        row = cursor.fetchone()
        
    if row:
        return web.Response(text=row[0], content_type='text/html')
    return web.Response(status=404)

async def get_profile_photo(request):
    username = request.match_info.get('username')
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute("SELECT profile_photo FROM profiles WHERE username = ?", (username,))
        row = cursor.fetchone()
        
    if row:
        return web.Response(body=row[0], content_type='image/png')
    return web.Response(status=404)

async def init_app():
    init_db()
    app = web.Application()
    app.add_routes([
        web.post('/add_profile', add_profile),
        web.get('/profile/{username}', get_profile),
        web.get('/profile-photo/{username}', get_profile_photo),
    ])
    return app

if __name__ == "__main__":
    app = None
    # Using a helper to run the app since we need to initialize the DB first
    import asyncio
    
    async def main():
        global app
        app = await init_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 5000)
        await site.start()
        print("Server started at http://0.0.0.0:5000")
        await asyncio.Event().wait()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass