import sqlite3
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import HTMLResponse

app = FastAPI(title="Profile Collection")

DB_PATH = "db.sqlite3"
# Limit upload size to prevent resource exhaustion (e.g., 5MB)
MAX_UPLOAD_SIZE = 5 * 1024 * 1024 

def init_db():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS profiles (
                    username TEXT PRIMARY KEY,
                    profile_page TEXT,
                    profile_photo BLOB
                )
            """)
            conn.commit()
    except Exception:
        # In a production environment, we would log this, but for this task 
        # we ensure the DB is initialized.
        pass

@app.on_event("startup")
def startup_event():
    init_db()

@app.post("/add_profile", status_code=201)
async def add_profile(
    username: str = Form(...),
    profile_page: str = Form(...),
    profile_photo: UploadFile = File(...)
):
    # 1. Resource Exhaustion: Bound request size for the file upload
    # Note: FastAPI/Starlette reads the file into memory or spool file.
    # We check the size of the uploaded content.
    content = await profile_photo.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="Invalid input: File too large")

    # 2. Input Validation: Ensure it is a PNG
    if profile_photo.content_type != "image/png":
        raise HTTPException(status_code=400, detail="Invalid input: Profile photo must be a PNG")

    # 3. SQL Injection: We use parameterized queries (the '?' placeholders) 
    # which is the standard way to prevent SQLi in sqlite3.
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)",
                (username, profile_page, content)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        # Specification requires 403 if profile already exists
        raise HTTPException(status_code=403, detail="Profile already exists, creation forbidden")
    except Exception:
        # Error handling: return documented error status code without leaking internals
        raise HTTPException(status_code=400, detail="Invalid input")
    
    return None

@app.get("/profile/{username}", response_class=HTMLResponse)
async def get_profile(username: str):
    # SQL Injection prevention via parameterized query
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT profile_page FROM profiles WHERE username = ?", (username,))
            row = cursor.fetchone()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid input")
        
    if row is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Security Note: The specification requires returning the HTML content provided by the user.
    # This is inherently a stored XSS risk. However, the prompt states:
    # "keep the behaviour for normal, valid requests EXACTLY as the specification says"
    # and "Do not add restrictions that reject legitimate requests".
    # Since the API is defined to return 'text/html' based on user-provided 'profile_page',
    # we must return the raw HTML to satisfy the functional requirement.
    return row[0]

@app.get("/profile-photo/{username}")
async def get_profile_photo(username: str):
    # SQL Injection prevention via parameterized query
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT profile_photo FROM profiles WHERE username = ?", (username,))
            row = cursor.fetchone()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid input")
        
    if row is None:
        raise HTTPException(status_code=404, detail="Profile photo not found")
    
    # Return binary data as image/png
    return Response(content=row[0], media_type="image/png")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)