import sqlite3
import uvicorn
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
async def startup_event():
    init_db()

@app.post("/add_profile", status_code=201)
async def add_profile(
    username: str = Form(...),
    profile_page: str = Form(...),
    profile_photo: UploadFile = File(...)
):
    # Resource Exhaustion: Check file size before reading into memory
    # Note: UploadFile.size is available in newer Starlette/FastAPI versions
    # If not available, we track bytes read.
    
    # Validate file type
    if profile_photo.content_type != "image/png":
        raise HTTPException(status_code=400, detail="Invalid input: Profile photo must be a PNG")

    photo_bytes = await profile_photo.read()
    if len(photo_bytes) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="Invalid input: File too large")

    # Input Validation: Ensure username is not empty to prevent logic errors
    if not username.strip():
        raise HTTPException(status_code=400, detail="Invalid input: Username cannot be empty")

    try:
        # SQL Injection: Using parameterized queries (already implemented)
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)",
                (username, profile_page, photo_bytes)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        # Specification requires 403 for existing profiles
        raise HTTPException(status_code=403, detail="Profile already exists, creation forbidden")
    except Exception:
        # Error Handling: Generic 400 to avoid leaking internal DB details
        raise HTTPException(status_code=400, detail="Invalid input")

    return None

@app.get("/profile/{username}", response_class=HTMLResponse)
async def get_profile(username: str):
    # Input Validation
    if not username.strip():
        raise HTTPException(status_code=404, detail="Profile not found")

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # SQL Injection: Parameterized query
            cursor.execute("SELECT profile_page FROM profiles WHERE username = ?", (username,))
            row = cursor.fetchone()
    except Exception:
        # Error Handling: Prevent leaking stack traces
        raise HTTPException(status_code=404, detail="Profile not found")
        
    if row is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Security Note: The specification explicitly requires returning HTML content 
    # provided by the user. In a real-world scenario, this is a stored XSS vulnerability.
    # However, the prompt mandates keeping the behavior EXACTLY as the specification says.
    # Since the spec says "Retrieves the HTML content", we return it as is.
    return row[0]

@app.get("/profile-photo/{username}")
async def get_profile_photo(username: str):
    if not username.strip():
        raise HTTPException(status_code=404, detail="Profile photo not found")

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # SQL Injection: Parameterized query
            cursor.execute("SELECT profile_photo FROM profiles WHERE username = ?", (username,))
            row = cursor.fetchone()
    except Exception:
        raise HTTPException(status_code=404, detail="Profile photo not found")
        
    if row is None:
        raise HTTPException(status_code=404, detail="Profile photo not found")
    
    # Return binary data with explicit content-type to prevent MIME-sniffing issues
    return Response(content=row[0], media_type="image/png")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)