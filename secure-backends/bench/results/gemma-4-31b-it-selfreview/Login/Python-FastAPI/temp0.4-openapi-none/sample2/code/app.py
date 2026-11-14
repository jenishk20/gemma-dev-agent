import os
import sqlite3
import datetime
import html
from typing import Optional
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr, Field
from jose import JWTError, jwt
from passlib.context import CryptContext

# Configuration
# Use a secure default if env is missing, but prioritize env variable
APP_SECRET = os.getenv("APP_SECRET", "fallback_secure_random_string_for_dev_only_12345")
DB_PATH = "db.sqlite3"
ALGORITHM = "HS256"

# Password hashing: bcrypt is a strong salted KDF
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="LoginAPI")

# Database Setup
def get_db():
    # Use a context manager for connection to ensure it closes
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
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

# Pydantic Models with basic size constraints to prevent resource exhaustion
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., max_length=128)

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=255)

class TokenResponse(BaseModel):
    token: str
    message: str

class MessageResponse(BaseModel):
    message: str

# Utility functions
def create_access_token(data: dict):
    to_encode = data.copy()
    # Set a strict expiry to prevent long-term token misuse
    expire = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, APP_SECRET, algorithm=ALGORITHM)

# HTML Templates (Escaping is handled via html.escape in the logic)
HTML_LOGIN = """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Login</title></head>
<body>
    <h2>Login</h2>
    <form method="post" action="/login_ui">
        Email: <input type="email" name="email" required><br>
        Password: <input type="password" name="password" required><br>
        <button type="submit">Login</button>
    </form>
    <p>Don't have an account? <a href="/register_ui">Register here</a></p>
</body>
</html>
"""

HTML_REGISTER = """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Register</title></head>
<body>
    <h2>Register</h2>
    <form method="post" action="/register_ui">
        Name: <input type="text" name="name" required><br>
        Email: <input type="email" name="email" required><br>
        Password: <input type="password" name="password" required><br>
        <button type="submit">Register</button>
    </form>
    <p>Already have an account? <a href="/login_ui">Login here</a></p>
</body>
</html>
"""

# API Endpoints
@app.post("/register", status_code=status.HTTP_201_CREATED, responses={201: MessageResponse, 400: MessageResponse})
async def register(user: RegisterRequest):
    # Passlib bcrypt handles salting and constant-time comparison internally
    hashed_password = pwd_context.hash(user.password)
    try:
        with get_db() as conn:
            # Parameterized query prevents SQL Injection
            conn.execute(
                "INSERT INTO users (email, password, name) VALUES (?, ?, ?)",
                (user.email, hashed_password, user.name)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        # Return documented error status code
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email already in use or invalid data"
        )
    except Exception:
        # Generic error to avoid leaking internal database details
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email already in use or invalid data"
        )
    return {"message": "Registration successful"}

@app.post("/login", responses={200: TokenResponse, 401: MessageResponse})
async def login(user: LoginRequest):
    try:
        with get_db() as conn:
            # Parameterized query prevents SQL Injection
            cursor = conn.execute("SELECT password FROM users WHERE email = ?", (user.email,))
            row = cursor.fetchone()
            
        # Constant-time comparison is handled by pwd_context.verify
        if not row or not pwd_context.verify(user.password, row['password']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid email or password"
            )
        
        token = create_access_token(data={"sub": user.email})
        return {"token": token, "message": "Login successful"}
    except HTTPException:
        raise
    except Exception:
        # Prevent leaking stack traces
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid email or password"
        )

# UI Endpoints
@app.get("/login_ui", response_class=HTMLResponse)
async def login_page():
    return HTML_LOGIN

@app.post("/login_ui")
async def login_ui_post(request: Request):
    try:
        form_data = await request.form()
        email = form_data.get("email", "")
        password = form_data.get("password", "")
        
        # Validate inputs via Pydantic to ensure constraints are met
        login_data = LoginRequest(email=email, password=password)
        res = await login(login_data)
        
        # Escape output to prevent XSS
        safe_token = html.escape(res['token'])
        return HTMLResponse(f"<h1>Login Successful</h1><p>Token: {safe_token}</p><a href='/login_ui'>Back</a>")
    except (HTTPException, ValueError) as e:
        # Handle both FastAPI HTTPExceptions and Pydantic ValidationErrors
        detail = e.detail if hasattr(e, 'detail') else str(e)
        safe_detail = html.escape(detail)
        status_code = e.status_code if hasattr(e, 'status_code') else 400
        return HTMLResponse(f"<h1>Error</h1><p>{safe_detail}</p><a href='/login_ui'>Back</a>", status_code=status_code)

@app.get("/register_ui", response_class=HTMLResponse)
async def register_page():
    return HTML_REGISTER

@app.post("/register_ui")
async def register_ui_post(request: Request):
    try:
        form_data = await request.form()
        email = form_data.get("email", "")
        password = form_data.get("password", "")
        name = form_data.get("name", "")
        
        # Validate inputs via Pydantic
        reg_data = RegisterRequest(email=email, password=password, name=name)
        await register(reg_data)
        return HTMLResponse("<h1>Registration Successful</h1><p>You can now <a href='/login_ui'>Login</a></p>")
    except (HTTPException, ValueError) as e:
        detail = e.detail if hasattr(e, 'detail') else str(e)
        safe_detail = html.escape(detail)
        status_code = e.status_code if hasattr(e, 'status_code') else 400
        return HTMLResponse(f"<h1>Error</h1><p>{safe_detail}</p><a href='/register_ui'>Back</a>", status_code=status_code)

if __name__ == "__main__":
    import uvicorn
    # Port 5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)