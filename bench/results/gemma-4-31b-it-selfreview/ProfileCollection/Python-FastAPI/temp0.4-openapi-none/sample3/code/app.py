import sqlite3
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI(title="Profile Collection")

DB_PATH = "db.sqlite3"
# Limit upload size to prevent resource exhaustion (e.g., 5MB)
MAX_FILE_SIZE = 5 * 1024 * 1024 

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
def startup_event():
    init_db()

@app.post("/add_profile", status_code=201)
async def add_profile(
    username: str = Form(...),
    profile_page: str = Form(...),
    profile_photo: UploadFile = File(...)
):
    # Resource Exhaustion: Check file size before reading into memory
    # Note: In a production environment, we would check the Content-Length header 
    # and use a streaming limit, but here we read and check.
    photo_bytes = await profile_photo.read()
    if len(photo_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Invalid input: File too large")

    # Validate file type
    if profile_photo.content_type != "image/png":
        raise HTTPException(status_code=400, detail="Invalid input: profile_photo must be a PNG")

    try:
        # SQL Injection: Using parameterized queries (?) prevents SQLi
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)",
                (username, profile_page, photo_bytes)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        # Specification: 403 if profile already exists
        raise HTTPException(status_code=403, detail="Profile already exists, creation forbidden")
    except Exception:
        # Error Handling: Catch all to prevent leaking internal stack traces
        raise HTTPException(status_code=400, detail="Invalid input")

    return Response(status_code=201)

@app.get("/profile/{username}", response_class=HTMLResponse)
async def get_profile(username: str):
    try:
        # SQL Injection: Using parameterized queries
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("SELECT profile_page FROM profiles WHERE username = ?", (username,))
            row = cursor.fetchone()
    except Exception:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    if row is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # The specification explicitly requires returning HTML content provided by the user.
    # While this is a stored XSS risk, the API contract defines this as the intended behavior.
    # We return the raw HTML as requested by the OpenAPI schema.
    return HTMLResponse(content=row[0])

@app.get("/profile-photo/{username}")
async def get_profile_photo(username: str):
    try:
        # SQL Injection: Using parameterized queries
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("SELECT profile_photo FROM profiles WHERE username = ?", (username,))
            row = cursor.fetchone()
    except Exception:
        raise HTTPException(status_code=404, detail="Profile photo not found")
        
    if row is None:
        raise HTTPException(status_code=404, detail="Profile photo not found")
    
    # Return binary data as image/png
    return Response(content=row[0], media_type="image/png")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)