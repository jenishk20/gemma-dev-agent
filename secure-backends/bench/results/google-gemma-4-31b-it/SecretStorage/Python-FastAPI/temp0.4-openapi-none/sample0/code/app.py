import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from jose import JWTError, jwt
from passlib.context import CryptContext

# Configuration
APP_SECRET = os.getenv("APP_SECRET", "default_secret_key_change_me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
DB_PATH = "db.sqlite3"

# Security setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
app = FastAPI(title="Secret Storage")

# Database Initialization
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS secrets (
                username TEXT PRIMARY KEY,
                secret_value TEXT NOT NULL,
                FOREIGN KEY (username) REFERENCES users(username)
            )
        """)
        conn.commit()

init_db()

# Pydantic Models
class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class SecretRequest(BaseModel):
    username: str
    secret: str

# Utility Functions
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, APP_SECRET, algorithm=ALGORITHM)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, APP_SECRET, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication token")

# Routes
@app.post("/register", status_code=201)
async def register(user_data: RegisterRequest):
    hashed_password = pwd_context.hash(user_data.password)
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO users (email, username, password_hash) VALUES (?, ?, ?)",
                (user_data.email, user_data.username, hashed_password)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Email already in use or invalid data")
    
    return {"message": "Registration successful"}

@app.post("/login")
async def login(credentials: LoginRequest):
    with get_db() as conn:
        user = conn.execute("SELECT password_hash, username FROM users WHERE email = ?", (credentials.email,)).fetchone()
        
    if not user or not pwd_context.verify(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token(data={"sub": user["username"]})
    return {"token": token, "message": "Login successful"}

@app.post("/set_secret")
async def set_secret(req: SecretRequest, current_user: str = Depends(get_current_user)):
    # Ensure user can only set their own secret
    if req.username != current_user:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO secrets (username, secret_value) VALUES (?, ?)",
            (req.username, req.secret)
        )
        conn.commit()
    
    return {"message": "Secret has been set successfully"}

@app.get("/get_secret")
async def get_secret(username: str, current_user: str = Depends(get_current_user)):
    # Ensure user can only retrieve their own secret
    if username != current_user:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    
    with get_db() as conn:
        row = conn.execute("SELECT secret_value FROM secrets WHERE username = ?", (username,)).fetchone()
        
    if row:
        return {"secret": row["secret_value"]}
    else:
        # Return empty or handle as not found, but schema implies success if authorized
        return {"secret": ""}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)