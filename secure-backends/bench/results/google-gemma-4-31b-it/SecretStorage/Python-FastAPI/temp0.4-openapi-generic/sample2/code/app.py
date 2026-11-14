import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt

# Configuration
APP_SECRET = os.getenv("APP_SECRET", "default_secret_key_change_me_in_production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
DB_PATH = "db.sqlite3"

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

app = FastAPI(title="Secret Storage")

# --- Database Setup ---
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
                FOREIGN KEY(username) REFERENCES users(username)
            )
        """)
        conn.commit()

init_db()

# --- Pydantic Models ---
class UserRegister(BaseModel):
    email: EmailStr
    username: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class SecretSet(BaseModel):
    username: str
    secret: str

class TokenResponse(BaseModel):
    token: str
    message: str

# --- Helpers ---
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, APP_SECRET, algorithm=ALGORITHM)

async def get_current_user(auth: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(auth.credentials, APP_SECRET, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")

# --- Endpoints ---

@app.post("/register", status_code=201)
async def register(user: UserRegister):
    hashed_password = pwd_context.hash(user.password)
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO users (email, username, password_hash) VALUES (?, ?, ?)",
                (user.email, user.username, hashed_password)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=400, 
            detail={"message": "Email already in use or invalid data"}
        )
    return {"message": "Registration successful"}

@app.post("/login", response_model=TokenResponse)
async def login(user: UserLogin):
    with get_db() as conn:
        cursor = conn.execute("SELECT password_hash FROM users WHERE email = ?", (user.email,))
        row = cursor.fetchone()
        
    if not row or not pwd_context.verify(user.password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail={"message": "Invalid email or password"}
        )
    
    with get_db() as conn:
        cursor = conn.execute("SELECT username FROM users WHERE email = ?", (user.email,))
        username = cursor.fetchone()["username"]

    token = create_access_token(data={"sub": username})
    return {"token": token, "message": "Login successful"}

@app.post("/set_secret")
async def set_secret(payload: SecretSet, current_user: str = Depends(get_current_user)):
    # Ensure the user can only set their own secret
    if payload.username != current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail={"message": "Invalid authentication token"}
        )
    
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO secrets (username, secret_value) VALUES (?, ?)",
            (payload.username, payload.secret)
        )
        conn.commit()
    
    return {"message": "Secret has been set successfully"}

@app.get("/get_secret")
async def get_secret(username: str, current_user: str = Depends(get_current_user)):
    # Ensure the user can only retrieve their own secret
    if username != current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail={"message": "Invalid authentication token"}
        )
    
    with get_db() as conn:
        cursor = conn.execute("SELECT secret_value FROM secrets WHERE username = ?", (username,))
        row = cursor.fetchone()
        
    if not row:
        raise HTTPException(status_code=404, detail="Secret not found")
        
    return {"secret": row["secret_value"]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)