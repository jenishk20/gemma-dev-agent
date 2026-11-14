import sqlite3
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import HTMLResponse

app = FastAPI(title="Profile Collection")

DB_PATH = "db.sqlite3"

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
    # Basic validation for file type based on schema (PNG)
    if profile_photo.content_type != "image/png":
        raise HTTPException(status_code=400, detail="Invalid input: profile_photo must be a PNG image")

    photo_bytes = await profile_photo.read()
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)",
                (username, profile_page, photo_bytes)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=403, detail="Profile already exists, creation forbidden")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid input")

    return Response(status_code=201)

@app.get("/profile/{username}", response_class=HTMLResponse)
async def get_profile(username: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT profile_page FROM profiles WHERE username = ?", (username,))
        row = cursor.fetchone()
        
    if row:
        return HTMLResponse(content=row[0])
    
    raise HTTPException(status_code=404, detail="Profile not found")

@app.get("/profile-photo/{username}")
async def get_profile_photo(username: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT profile_photo FROM profiles WHERE username = ?", (username,))
        row = cursor.fetchone()
        
    if row:
        return Response(content=row[0], media_type="image/png")
    
    raise HTTPException(status_code=404, detail="Profile photo not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)