import sqlite3
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import HTMLResponse

app = FastAPI(title="Profile Collection")

DB_PATH = "db.sqlite3"
# Limit upload size to 5MB to prevent resource exhaustion (DoS)
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
async def startup_event():
    init_db()

@app.post("/add_profile", status_code=201)
async def add_profile(
    username: str = Form(...),
    profile_page: str = Form(...),
    profile_photo: UploadFile = File(...)
):
    # Basic validation for empty inputs
    if not username.strip() or not profile_page:
        raise HTTPException(status_code=400, detail="Invalid input")
    
    # Validate file type to prevent uploading malicious files as images
    if profile_photo.content_type != "image/png":
        raise HTTPException(status_code=400, detail="Invalid input: Photo must be a PNG")

    # Resource Exhaustion: Limit the size of the uploaded file
    photo_bytes = await profile_photo.read()
    if len(photo_bytes) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File too large")
    
    try:
        # SQL Injection Prevention: Using parameterized queries (?)
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)",
                (username, profile_page, photo_bytes)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        # Handle unique constraint violation for username
        raise HTTPException(status_code=403, detail="Profile already exists, creation forbidden")
    except Exception:
        # Generic error handling to prevent leaking internal stack traces
        raise HTTPException(status_code=400, detail="Invalid input")

@app.get("/profile/{username}", response_class=HTMLResponse)
async def get_profile(username: str):
    try:
        # SQL Injection Prevention: Using parameterized queries
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("SELECT profile_page FROM profiles WHERE username = ?", (username,))
            row = cursor.fetchone()
            if row:
                # The specification requires returning the HTML content as provided.
                # Since the API is designed to serve user-provided HTML, we return it.
                # Note: In a real-world scenario, this is a stored XSS risk, 
                # but the OpenAPI spec explicitly defines the response as text/html.
                return row[0]
            raise HTTPException(status_code=404, detail="Profile not found")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=404, detail="Profile not found")

@app.get("/profile-photo/{username}")
async def get_profile_photo(username: str):
    try:
        # SQL Injection Prevention: Using parameterized queries
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("SELECT profile_photo FROM profiles WHERE username = ?", (username,))
            row = cursor.fetchone()
            if row:
                # Return binary data with explicit media type
                return Response(content=row[0], media_type="image/png")
            raise HTTPException(status_code=404, detail="Profile photo not found")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=404, detail="Profile photo not found")

if __name__ == "__main__":
    # Run on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)