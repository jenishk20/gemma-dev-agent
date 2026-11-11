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
# Use a strong secret from environment; provide a fallback for local dev but ensure it's long
APP_SECRET = os.getenv("APP_SECRET", "a_very_long_and_secure_random_fallback_secret_key_123456789")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
DB_PATH = "db.sqlite3"

# Password hashing with bcrypt (strong salted KDF)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

app = FastAPI(title="Secret Storage")

# --- Database Setup ---
def get_db():
    # Using a context manager for the connection to ensure it's closed
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        # Use parameterized-like schema creation
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

# --- Models ---
# Added constraints to prevent resource exhaustion (max lengths)
class UserRegister(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=128)

class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., max_length=128)

class SecretSet(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    secret: str = Field(..., max_length=10000) # Bound request size for the secret

class TokenResponse(BaseModel):
    token: str
    message: str

# --- Helpers ---
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    # jose.jwt.encode handles the signature and algorithm correctly
    return jwt.encode(to_encode, APP_SECRET, algorithm=ALGORITHM)

async def get_current_user(auth: HTTPAuthorizationCredentials = Depends(security)):
    try:
        # Explicitly specify the algorithm to prevent algorithm switching attacks
        payload = jwt.decode(auth.credentials, APP_SECRET, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        return username
    except JWTError:
        # Catch all JWT errors (expired, invalid signature, etc) and return 401
        raise HTTPException(status_code=401, detail="Invalid authentication token")

# --- Endpoints ---

@app.post("/register", status_code=201)
async def register(user: UserRegister, db: sqlite3.Connection = Depends(get_db)):
    # Password hashing is handled by passlib (bcrypt)
    hashed_password = pwd_context.hash(user.password)
    try:
        # Use parameterized queries to prevent SQL Injection
        db.execute(
            "INSERT INTO users (email, username, password_hash) VALUES (?, ?, ?)",
            (user.email, user.username, hashed_password)
        )
        db.commit()
    except sqlite3.IntegrityError:
        # Handle duplicate email/username as per OpenAPI spec
        raise HTTPException(status_code=400, detail="Email already in use or invalid data")
    except Exception:
        # Generic error to avoid leaking internal DB details
        raise HTTPException(status_code=400, detail="Invalid data")
    return {"message": "Registration successful"}

@app.post("/login", response_model=TokenResponse)
async def login(user: UserLogin, db: sqlite3.Connection = Depends(get_db)):
    # Parameterized query to prevent SQL Injection
    result = db.execute("SELECT password_hash, username FROM users WHERE email = ?", (user.email,)).fetchone()
    
    # Constant-time comparison is handled by passlib.verify
    if not result or not pwd_context.verify(user.password, result["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token(data={"sub": result["username"]})
    return {"token": token, "message": "Login successful"}

@app.post("/set_secret")
async def set_secret(data: SecretSet, current_user: str = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)):
    # Authorization check: ensure the caller owns the resource they are changing
    # We do not trust the 'username' provided in the body if it differs from the token
    if data.username != current_user:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    
    # Parameterized query to prevent SQL Injection
    db.execute(
        "INSERT OR REPLACE INTO secrets (username, secret_value) VALUES (?, ?)",
        (data.username, data.secret)
    )
    db.commit()
    return {"message": "Secret has been set successfully"}

@app.get("/get_secret")
async def get_secret(username: str, current_user: str = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)):
    # Authorization check: ensure the caller owns the resource they are reading
    if username != current_user:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    
    # Parameterized query to prevent SQL Injection
    result = db.execute("SELECT secret_value FROM secrets WHERE username = ?", (username,)).fetchone()
    if not result:
        # Return 404 or 401? Spec says 200 for success, 401 for unauthorized.
        # If the user is authorized but has no secret, we return a 404 or empty.
        # However, to strictly follow the "Unauthorized" logic for any failure in access:
        raise HTTPException(status_code=404, detail="Secret not found")
    
    return {"secret": result["secret_value"]}

if __name__ == "__main__":
    import uvicorn
    # Run on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)