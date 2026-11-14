import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.responses import JSONResponse
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

# Pydantic Models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str

class TokenResponse(BaseModel):
    token: str
    message: str

class MessageResponse(BaseModel):
    message: str

# Database Helper
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
                password TEXT NOT NULL,
                name TEXT NOT NULL
            )
        """)
        conn.commit()

# JWT Logic
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, APP_SECRET, algorithm=ALGORITHM)

# FastAPI App
app = FastAPI(title="LoginAPI", version="1.0.11")

@app.on_event("startup")
def startup_event():
    init_db()

@app.post("/register", status_code=status.HTTP_201_CREATED, responses={201: MessageResponse, 400: MessageResponse})
def register(request: RegisterRequest):
    hashed_password = pwd_context.hash(request.password)
    
    with sqlite3.connect(DB_PATH) as conn:
        try:
            conn.execute(
                "INSERT INTO users (email, password, name) VALUES (?, ?, ?)",
                (request.email, hashed_password, request.name)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Email already in use or invalid data"
            )
            
    return {"message": "Registration successful"}

@app.post("/login", responses={200: TokenResponse, 401: MessageResponse})
def login(request: LoginRequest):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT password FROM users WHERE email = ?", (request.email,))
        user = cursor.fetchone()

    if not user or not pwd_context.verify(request.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    token = create_access_token(data={"sub": request.email})
    return {"token": token, "message": "Login successful"}

# Custom exception handler to match the OpenAPI schema's response structure (message instead of detail)
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)