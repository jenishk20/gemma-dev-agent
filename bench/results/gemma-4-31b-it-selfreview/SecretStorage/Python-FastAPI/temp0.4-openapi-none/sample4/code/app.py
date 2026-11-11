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
# Using a strong default if env is missing, though env is expected
APP_SECRET = os.getenv("APP_SECRET", "fallback_secure_random_string_for_dev_only")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
DB_PATH = "db.sqlite3"

# Password hashing with bcrypt (strong salted KDF)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer()

app = FastAPI(title="Secret Storage")

# --- Database Setup ---
def init_db():
    # Use a context manager to ensure connection closes
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
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
# Added constraints to prevent resource exhaustion via massive strings
class UserRegister(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=1024)

class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., max_length=1024)

class SecretSet(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    secret: str = Field(..., max_length=10000)

class TokenResponse(BaseModel):
    token: str
    message: str

# --- Helpers ---
def create_access_token(data: dict):
    to_encode = data.copy()
    # Use UTC for consistency and set expiry
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, APP_SECRET, algorithm=ALGORITHM)

async def get_current_user(auth: HTTPAuthorizationCredentials = Depends(security)):
    token = auth.credentials
    try:
        # Verify token signature and algorithm explicitly
        payload = jwt.decode(token, APP_SECRET, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        return username
    except JWTError:
        # Return the specific error message required by the OpenAPI schema
        raise HTTPException(status_code=401, detail="Invalid authentication token")

# --- Endpoints ---

@app.post("/register", status_code=201)
async def register(user: UserRegister):
    hashed_pw = pwd_context.hash(user.password)
    try:
        with sqlite3.connect(DB_PATH) as conn:
            # Parameterized query to prevent SQL injection
            conn.execute(
                "INSERT INTO users (email, username, password) VALUES (?, ?, ?)",
                (user.email, user.username, hashed_pw)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        # Handle duplicate email/username as per schema
        raise HTTPException(status_code=400, detail="Email already in use or invalid data")
    except Exception:
        # Generic error to avoid leaking internal database details
        raise HTTPException(status_code=400, detail="Email already in use or invalid data")
    
    return {"message": "Registration successful"}

@app.post("/login", response_model=TokenResponse)
async def login(user: UserLogin):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            # Parameterized query
            cursor = conn.execute("SELECT username, password FROM users WHERE email = ?", (user.email,))
            db_user = cursor.fetchone()
            
        # Use passlib's verify which handles constant-time comparison
        if not db_user or not pwd_context.verify(user.password, db_user["password"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        token = create_access_token(data={"sub": db_user["username"]})
        return {"token": token, "message": "Login successful"}
    except HTTPException as he:
        raise he
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid email or password")

@app.post("/set_secret")
async def set_secret(data: SecretSet, current_user: str = Depends(get_current_user)):
    # Authorization: Ensure the authenticated user is only modifying their own secret
    # This prevents "Insecure Direct Object Reference" (IDOR)
    if data.username != current_user:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            # Parameterized query
            conn.execute(
                "INSERT OR REPLACE INTO secrets (username, secret_value) VALUES (?, ?)",
                (data.username, data.secret)
            )
            conn.commit()
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")
        
    return {"message": "Secret has been set successfully"}

@app.get("/get_secret")
async def get_secret(username: str, current_user: str = Depends(get_current_user)):
    # Authorization: Ensure the authenticated user is only reading their own secret
    if username != current_user:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            # Parameterized query
            cursor = conn.execute("SELECT secret_value FROM secrets WHERE username = ?", (username,))
            row = cursor.fetchone()
            
        if row:
            return {"secret": row["secret_value"]}
        else:
            # Return empty or specific message if no secret exists, but still 200 as per schema
            return {"secret": ""}
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")

if __name__ == "__main__":
    import uvicorn
    # Port 5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)