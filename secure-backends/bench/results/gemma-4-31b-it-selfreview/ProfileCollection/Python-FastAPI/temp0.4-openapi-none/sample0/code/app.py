import sqlite3
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import HTMLResponse

app = FastAPI(title="Profile Collection")

DB_PATH = "db.sqlite3"
# Limit upload size to prevent resource exhaustion (e.g., 5MB)
MAX_UPLOAD_SIZE = 5 * 1024 * 1024 

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                username TEXT PRIMARY KEY,
                profile_page TEXT,
                profile_photo BLOB
            )
        """)
        conn.commit()

@app.on_event("startup")
def startup():
    init_db()

@app.post("/add_profile", status_code=201)
async def add_profile(
    username: str = Form(...),
    profile_page: str = Form(...),
    profile_photo: UploadFile = File(...)
):
    # Resource Exhaustion: Validate file size before reading into memory
    # Note: Some clients/proxies might not send content-length, 
    # so we check the actual read size.
    
    # Basic validation for file type based on schema (PNG)
    if profile_photo.content_type != "image/png":
        raise HTTPException(status_code=400, detail="Invalid input: profile_photo must be a PNG image")

    try:
        photo_bytes = await profile_photo.read()
        if len(photo_bytes) > MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=400, detail="File too large")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid input")

    # SQL Injection: Using parameterized queries (already implemented via ?)
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)",
                (username, profile_page, photo_bytes)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        # 403 as per OpenAPI spec for existing profile
        raise HTTPException(status_code=403, detail="Profile already exists, creation forbidden")
    except Exception:
        # Generic error handling to avoid leaking internal details
        raise HTTPException(status_code=400, detail="Invalid input")

    return Response(status_code=201)

@app.get("/profile/{username}", response_class=HTMLResponse)
async def get_profile(username: str):
    # SQL Injection: Using parameterized queries
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("SELECT profile_page FROM profiles WHERE username = ?", (username,))
            row = cursor.fetchone()
    except Exception:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    if row:
        # The specification explicitly asks for the HTML content to be returned.
        # Since the API's purpose is to serve user-provided HTML, we return it as is.
        # In a real-world scenario, this is a stored XSS vulnerability, but the 
        # prompt requires keeping behavior EXACTLY as specified.
        return HTMLResponse(content=row[0])
    
    raise HTTPException(status_code=404, detail="Profile not found")

@app.get("/profile-photo/{username}")
async def get_profile_photo(username: str):
    # SQL Injection: Using parameterized queries
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("SELECT profile_photo FROM profiles WHERE username = ?", (username,))
            row = cursor.fetchone()
    except Exception:
        raise HTTPException(status_code=404, detail="Profile photo not found")
        
    if row:
        return Response(content=row[0], media_type="image/png")
    
    raise HTTPException(status_code=404, detail="Profile photo not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)