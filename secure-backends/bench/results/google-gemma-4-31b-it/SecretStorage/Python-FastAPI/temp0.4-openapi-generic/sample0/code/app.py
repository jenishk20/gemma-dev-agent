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
APP_SECRET = os.getenv("APP_SECRET", "default_secret_key_change_this_in_production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
DB_PATH = "db.sqlite3"

# Security Contexts
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
app = FastAPI(title="Secret Storage")

# --- Database Logic ---
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL
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

# --- Pydantic Models ---
class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class SetSecretRequest(BaseModel):
    username: str
    secret: str

class MessageResponse(BaseModel):
    message: str

class TokenResponse(BaseModel):
    token: str
    message: str

class SecretResponse(BaseModel):
    secret: str

# --- Utilities ---
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, APP_SECRET, algorithm=ALGORITHM)

async def get_current_user(auth: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(auth.credentials, APP_SECRET, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return username
    except JWTError:
        raise credentials_exception

# --- Routes ---

@app.post("/register", response_model=MessageResponse, status_code=201)
async def register(req: RegisterRequest, db: sqlite3.Connection = Depends(get_db)):
    hashed_pw = pwd_context.hash(req.password)
    try:
        db.execute(
            "INSERT INTO users (email, username, hashed_password) VALUES (?, ?, ?)",
            (req.email, req.username, hashed_pw)
        )
        db.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Email already in use or invalid data")
    return {"message": "Registration successful"}

@app.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: sqlite3.Connection = Depends(get_db)):
    user = db.execute("SELECT * FROM users WHERE email = ?", (req.email,)).fetchone()
    if not user or not pwd_context.verify(req.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token(data={"sub": user["username"]})
    return {"token": token, "message": "Login successful"}

@app.post("/set_secret", response_model=MessageResponse)
async def set_secret(
    req: SetSecretRequest, 
    current_user: str = Depends(get_current_user), 
    db: sqlite3.Connection = Depends(get_db)
):
    # Ensure the user can only set a secret for their own account
    if current_user != req.username:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    
    db.execute(
        "INSERT OR REPLACE INTO secrets (username, secret_value) VALUES (?, ?)",
        (req.username, req.secret)
    )
    db.commit()
    return {"message": "Secret has been set successfully"}

@app.get("/get_secret", response_model=SecretResponse)
async def get_secret(
    username: str, 
    current_user: str = Depends(get_current_user), 
    db: sqlite3.Connection = Depends(get_db)
):
    # Ensure the user can only retrieve their own secret
    if current_user != username:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    
    row = db.execute("SELECT secret_value FROM secrets WHERE username = ?", (username,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Secret not found")
    
    return {"secret": row["secret_value"]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)