import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, status, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr, Field
from jose import JWTError, jwt
from passlib.context import CryptContext

# Configuration
# Use a strong secret from environment or a secure fallback
APP_SECRET = os.getenv("APP_SECRET", "fallback-secret-key-for-dev-only-do-not-use-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
DB_NAME = "db.sqlite3"

# Password hashing using bcrypt (strong salted KDF)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="LoginAPI")

# Database helper
def get_db_connection():
    # sqlite3.connect is safe from path traversal here as DB_NAME is a hardcoded constant
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                name TEXT NOT NULL
            )
        """)
        conn.commit()

init_db()

# Pydantic Models with basic constraints to prevent resource exhaustion (max lengths)
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=128)

class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)

class TokenResponse(BaseModel):
    token: str
    message: str

class MessageResponse(BaseModel):
    message: str

# JWT Logic
def create_access_token(data: dict):
    to_encode = data.copy()
    # Use UTC for consistency and set expiration
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, APP_SECRET, algorithm=ALGORITHM)

# HTML Templates as strings
# Note: We use a simple approach to avoid Jinja2 template injection by not using 
# dynamic user input inside the templates themselves, but rather serving static strings.
HTML_LOGIN_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Login</title></head>
<body>
    <h2>Login</h2>
    <form action="/login_form" method="post">
        <input type="email" name="email" placeholder="Email" required><br>
        <input type="password" name="password" placeholder="Password" required><br>
        <button type="submit">Login</button>
    </form>
    <p>Don't have an account? <a href="/register_page">Register here</a></p>
</body>
</html>
"""

HTML_REGISTER_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Register</title></head>
<body>
    <h2>Register</h2>
    <form action="/register_form" method="post">
        <input type="text" name="name" placeholder="Full Name" required><br>
        <input type="email" name="email" placeholder="Email" required><br>
        <input type="password" name="password" placeholder="Password" required><br>
        <button type="submit">Register</button>
    </form>
    <p>Already have an account? <a href="/login_page">Login here</a></p>
</body>
</html>
"""

# API Endpoints
@app.post("/register", status_code=status.HTTP_201_CREATED, response_model=MessageResponse)
async def register(user: UserRegister):
    # bcrypt handles salting and secure hashing
    hashed_password = pwd_context.hash(user.password)
    try:
        with get_db_connection() as conn:
            # Parameterized query to prevent SQL Injection
            conn.execute(
                "INSERT INTO users (email, password, name) VALUES (?, ?, ?)",
                (user.email, hashed_password, user.name)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        # Return documented 400 for email collision
        raise HTTPException(status_code=400, detail="Email already in use or invalid data")
    except Exception:
        # Generic error to avoid leaking internal DB details
        raise HTTPException(status_code=400, detail="Invalid data")
    
    return {"message": "Registration successful"}

@app.post("/login", response_model=TokenResponse)
async def login(user: UserLogin):
    try:
        with get_db_connection() as conn:
            # Parameterized query to prevent SQL Injection
            cursor = conn.execute("SELECT password FROM users WHERE email = ?", (user.email,))
            row = cursor.fetchone()
            
            # Constant-time comparison is handled by passlib.verify
            if not row or not pwd_context.verify(user.password, row['password']):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, 
                    detail="Invalid email or password"
                )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
            
    token = create_access_token(data={"sub": user.email})
    return {"token": token, "message": "Login successful"}

# Frontend Routes
@app.get("/login_page", response_class=HTMLResponse)
async def login_page():
    return HTML_LOGIN_PAGE

@app.get("/register_page", response_class=HTMLResponse)
async def register_page():
    return HTML_REGISTER_PAGE

# Form Handlers with basic XSS protection (escaping output)
import html

@app.post("/login_form", response_class=HTMLResponse)
async def login_form_handler(email: str = Form(...), password: str = Form(...)):
    try:
        # Validate inputs via Pydantic model before processing
        user_data = UserLogin(email=email, password=password)
        res = await login(user_data)
        # Escape output to prevent XSS
        return f"<h1>Login Successful</h1><p>Token: {html.escape(res.token)}</p>"
    except HTTPException as e:
        return f"<h1>Error</h1><p>{html.escape(str(e.detail))}</p><a href='/login_page'>Back</a>"
    except Exception:
        return "<h1>Error</h1><p>Invalid input</p><a href='/login_page'>Back</a>"

@app.post("/register_form", response_class=HTMLResponse)
async def register_form_handler(name: str = Form(...), email: str = Form(...), password: str = Form(...)):
    try:
        # Validate inputs via Pydantic model before processing
        user_data = UserRegister(email=email, password=password, name=name)
        await register(user_data)
        return "<h1>Registration Successful</h1><p><a href='/login_page'>Login now</a></p>"
    except HTTPException as e:
        return f"<h1>Error</h1><p>{html.escape(str(e.detail))}</p><a href='/register_page'>Back</a>"
    except Exception:
        return "<h1>Error</h1><p>Invalid input</p><a href='/register_page'>Back</a>"

if __name__ == "__main__":
    import uvicorn
    # Run on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)