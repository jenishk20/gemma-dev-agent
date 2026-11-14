import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from jose import JWTError, jwt
from passlib.context import CryptContext

# Configuration
# Ensure APP_SECRET is treated as a byte-string or strong string for JWT
APP_SECRET = os.getenv("APP_SECRET", "default_secret_key_change_me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
DB_PATH = "db.sqlite3"

# Security setup
# bcrypt is a strong salted KDF
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

app = FastAPI(title="Secret Storage")

# Database Initialization
def init_db():
    # Using a context manager for the connection
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Use strict typing and constraints
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS secrets (
                username TEXT PRIMARY KEY,
                secret_value TEXT NOT NULL,
                FOREIGN KEY (username) REFERENCES users(username)
            )
        """)
        conn.commit()

init_db()

# Pydantic Models with basic size constraints to prevent resource exhaustion (DoS)
class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=128)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., max_length=128)

class SecretRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    secret: str = Field(..., max_length=10000) # Bound secret size

# Utility Functions
def create_access_token(data: dict):
    to_encode = data.copy()
    # Set expiry to prevent long-lived token abuse
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, APP_SECRET, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        # Verify token signature and algorithm explicitly
        payload = jwt.decode(token, APP_SECRET, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        return username
    except JWTError:
        # Catching all JWT errors (expired, invalid signature, etc) and returning 401
        raise HTTPException(status_code=401, detail="Invalid authentication token")

# Routes
@app.post("/register", status_code=201)
async def register(req: RegisterRequest):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            hashed_pw = pwd_context.hash(req.password)
            # Use parameterized queries to prevent SQL Injection
            cursor.execute(
                "INSERT INTO users (email, username, hashed_password) VALUES (?, ?, ?)",
                (req.email, req.username, hashed_pw)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        # Handle unique constraint violations (email/username already exists)
        raise HTTPException(status_code=400, detail="Email already in use or invalid data")
    except Exception:
        # Generic error handling to prevent leaking internal stack traces
        raise HTTPException(status_code=400, detail="Email already in use or invalid data")
    
    return {"message": "Registration successful"}

@app.post("/login")
async def login(req: LoginRequest):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            # Parameterized query
            cursor.execute("SELECT hashed_password, username FROM users WHERE email = ?", (req.email,))
            user = cursor.fetchone()
            
            # Constant-time comparison is handled by passlib.verify
            if not user or not pwd_context.verify(req.password, user["hashed_password"]):
                raise HTTPException(status_code=401, detail="Invalid email or password")
            
            token = create_access_token(data={"sub": user["username"]})
            return {"token": token, "message": "Login successful"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid email or password")

@app.post("/set_secret")
async def set_secret(req: SecretRequest, current_user: str = Depends(get_current_user)):
    # Authorization: Ensure the token owner matches the username they are trying to set a secret for
    if req.username != current_user:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # Parameterized query
            cursor.execute(
                "INSERT OR REPLACE INTO secrets (username, secret_value) VALUES (?, ?)",
                (req.username, req.secret)
            )
            conn.commit()
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")
        
    return {"message": "Secret has been set successfully"}

@app.get("/get_secret")
async def get_secret(username: str, current_user: str = Depends(get_current_user)):
    # Authorization: Ensure the token owner is requesting their own secret
    if username != current_user:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            # Parameterized query
            cursor.execute("SELECT secret_value FROM secrets WHERE username = ?", (username,))
            row = cursor.fetchone()
            if row:
                return {"secret": row["secret_value"]}
            else:
                # If no secret is set, return empty string as per implied behavior
                return {"secret": ""}
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    # Run on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)