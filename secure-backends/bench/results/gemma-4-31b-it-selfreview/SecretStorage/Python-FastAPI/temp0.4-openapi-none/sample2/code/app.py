import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from jose import JWTError, jwt
from passlib.context import CryptContext
import uvicorn

# Configuration
# Use a strong secret from environment; fallback is only for local dev
APP_SECRET = os.getenv("APP_SECRET", "default_secret_key_for_dev")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
DB_PATH = "db.sqlite3"

# Password hashing with bcrypt (strong salted KDF)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

app = FastAPI(title="Secret Storage")

# Database Setup
def get_db():
    # Using a context manager for the connection
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        # Use parameterized queries/DDL
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS secrets (
                username TEXT PRIMARY KEY,
                secret_value TEXT NOT NULL,
                FOREIGN KEY (username) REFERENCES users (username)
            )
        ''')
        conn.commit()

init_db()

# Pydantic Models with basic constraints to prevent resource exhaustion (DoS)
class UserRegister(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=1024)

class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., max_length=1024)

class SecretSet(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    secret: str = Field(..., max_length=10000) # Bound request size

class TokenResponse(BaseModel):
    token: str
    message: str

# Utility Functions
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    # jwt.encode handles signature and algorithm
    return jwt.encode(to_encode, APP_SECRET, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        # Verify token signature and expiration
        payload = jwt.decode(credentials.credentials, APP_SECRET, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        # Return documented error status code
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )

# API Endpoints
@app.post("/register", status_code=201)
async def register(user: UserRegister):
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            # Salted hashing via passlib
            hashed_pw = pwd_context.hash(user.password)
            # Parameterized query to prevent SQL Injection
            cursor.execute(
                "INSERT INTO users (email, username, password_hash) VALUES (?, ?, ?)",
                (user.email, user.username, hashed_pw)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        # Handle duplicate email/username as per schema
        raise HTTPException(
            status_code=400, 
            detail="Email already in use or invalid data"
        )
    except Exception:
        # Generic error to avoid leaking internal details
        raise HTTPException(status_code=400, detail="Email already in use or invalid data")
        
    return {"message": "Registration successful"}

@app.post("/login", response_model=TokenResponse)
async def login(user: UserLogin):
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            # Parameterized query
            cursor.execute("SELECT password_hash, username FROM users WHERE email = ?", (user.email,))
            row = cursor.fetchone()
            
            # Constant-time comparison is handled by passlib.verify
            if not row or not pwd_context.verify(user.password, row['password_hash']):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
            
            token = create_access_token(data={"sub": row['username']})
            return {"token": token, "message": "Login successful"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

@app.post("/set_secret")
async def set_secret(payload: SecretSet, token_data: dict = Depends(verify_token)):
    # Authorization: Ensure the caller owns the resource (username in token == username in body)
    # This prevents users from setting secrets for other users.
    if token_data.get("sub") != payload.username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )

    try:
        with get_db() as conn:
            cursor = conn.cursor()
            # Parameterized query to prevent SQL Injection
            cursor.execute(
                "INSERT OR REPLACE INTO secrets (username, secret_value) VALUES (?, ?)",
                (payload.username, payload.secret)
            )
            conn.commit()
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")
    
    return {"message": "Secret has been set successfully"}

@app.get("/get_secret")
async def get_secret(username: str, token_data: dict = Depends(verify_token)):
    # Authorization: Ensure the caller owns the resource they are trying to read
    if token_data.get("sub") != username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )

    try:
        with get_db() as conn:
            cursor = conn.cursor()
            # Parameterized query
            cursor.execute("SELECT secret_value FROM secrets WHERE username = ?", (username,))
            row = cursor.fetchone()
            
            if row:
                return {"secret": row['secret_value']}
            else:
                # Return empty string if no secret exists, maintaining API behavior
                return {"secret": ""}
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    # Run on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)