import os
import sqlite3
import datetime
import html
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from jose import jwt, JWTError
from passlib.context import CryptContext

# Configuration
# Ensure APP_SECRET is handled securely. 
# If not provided in env, we use a fallback, but in production, this must be set.
APP_SECRET = os.getenv("APP_SECRET", "default_secret_key_for_dev")
ALGORITHM = "HS256"
DB_PATH = "db.sqlite3"

# Password hashing: passlib bcrypt uses a strong salted KDF.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="LoginAPI")

# Database Setup
def get_db_connection():
    # Use a connection factory to ensure we don't share connections across threads
    conn = sqlite3.connect(DB_PATH)
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

# Pydantic Models (Provides automatic validation and type checking)
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str

class LoginResponse(BaseModel):
    token: str
    message: str

class RegisterResponse(BaseModel):
    message: str

# Helper functions
def create_access_token(data: dict):
    to_encode = data.copy()
    # Set a reasonable expiry (24 hours)
    expire = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, APP_SECRET, algorithm=ALGORITHM)

# HTML Templates (Escaping is handled via html.escape for dynamic content)
HTML_LOGIN_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Login</title>
    <style>body { font-family: sans-serif; display: flex; justify-content: center; padding-top: 50px; }</style>
</head>
<body>
    <div style="width: 300px;">
        <h2>Login</h2>
        <form method="POST" action="/login_ui">
            <input type="email" name="email" placeholder="Email" required style="width:100%; margin-bottom:10px;"><br>
            <input type="password" name="password" placeholder="Password" required style="width:100%; margin-bottom:10px;"><br>
            <button type="submit" style="width:100%;">Login</button>
        </form>
        <p>Don't have an account? <a href="/register_ui">Register here</a></p>
    </div>
</body>
</html>
"""

HTML_REGISTER_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Register</title>
    <style>body { font-family: sans-serif; display: flex; justify-content: center; padding-top: 50px; }</style>
</head>
<body>
    <div style="width: 300px;">
        <h2>Register</h2>
        <form method="POST" action="/register_ui">
            <input type="text" name="name" placeholder="Full Name" required style="width:100%; margin-bottom:10px;"><br>
            <input type="email" name="email" placeholder="Email" required style="width:100%; margin-bottom:10px;"><br>
            <input type="password" name="password" placeholder="Password" required style="width:100%; margin-bottom:10px;"><br>
            <button type="submit" style="width:100%;">Register</button>
        </form>
        <p>Already have an account? <a href="/login_ui">Login here</a></p>
    </div>
</body>
</html>
"""

# API Endpoints
@app.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(user: RegisterRequest):
    # Passlib bcrypt handles salting and secure hashing
    hashed_pw = pwd_context.hash(user.password)
    try:
        with get_db_connection() as conn:
            # Parameterized query prevents SQL Injection
            conn.execute("INSERT INTO users (email, password, name) VALUES (?, ?, ?)", 
                         (user.email, hashed_pw, user.name))
            conn.commit()
    except sqlite3.IntegrityError:
        # Return documented error status code
        raise HTTPException(status_code=400, detail="Email already in use or invalid data")
    except Exception:
        # Generic error to avoid leaking internal details
        raise HTTPException(status_code=400, detail="Registration failed")
    return {"message": "Registration successful"}

@app.post("/login", response_model=LoginResponse)
async def login(user: LoginRequest):
    try:
        with get_db_connection() as conn:
            # Parameterized query prevents SQL Injection
            cursor = conn.execute("SELECT password FROM users WHERE email = ?", (user.email,))
            row = cursor.fetchone()
            
        # pwd_context.verify uses constant-time comparison to prevent timing attacks
        if row and pwd_context.verify(user.password, row['password']):
            token = create_access_token({"sub": user.email})
            return {"token": token, "message": "Login successful"}
    except Exception:
        # Generic error to avoid leaking internal details
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    raise HTTPException(status_code=401, detail="Invalid email or password")

# UI Endpoints
@app.get("/login_ui", response_class=HTMLResponse)
async def get_login_page():
    return HTML_LOGIN_PAGE

@app.post("/login_ui", response_class=HTMLResponse)
async def post_login_page(request: Request):
    form_data = await request.form()
    email = form_data.get("email")
    password = form_data.get("password")
    
    if not email or not password:
        return "<h1>Error</h1><p>Missing credentials</p><a href='/login_ui'>Back</a>"

    try:
        # Validate input via Pydantic before passing to logic
        login_req = LoginRequest(email=email, password=password)
        res = await login(login_req)
        # Escape dynamic content to prevent XSS
        safe_token = html.escape(res.token)
        return f"<h1>Welcome!</h1><p>Login successful. Your token is: {safe_token}</p>"
    except (HTTPException, ValueError) as e:
        # Escape error messages to prevent XSS
        detail = html.escape(str(e.detail if hasattr(e, 'detail') else str(e)))
        return f"<h1>Error</h1><p>{detail}</p><a href='/login_ui'>Back</a>"

@app.get("/register_ui", response_class=HTMLResponse)
async def get_register_page():
    return HTML_REGISTER_PAGE

@app.post("/register_ui", response_class=HTMLResponse)
async def post_register_page(request: Request):
    form_data = await request.form()
    name = form_data.get("name")
    email = form_data.get("email")
    password = form_data.get("password")
    
    if not all([name, email, password]):
        return "<h1>Error</h1><p>All fields are required</p><a href='/register_ui'>Back</a>"
    
    try:
        # Validate input via Pydantic before passing to logic
        reg_req = RegisterRequest(email=email, password=password, name=name)
        await register(reg_req)
        return "<h1>Success!</h1><p>Registration successful. <a href='/login_ui'>Login now</a></p>"
    except (HTTPException, ValueError) as e:
        # Escape error messages to prevent XSS
        detail = html.escape(str(e.detail if hasattr(e, 'detail') else str(e)))
        return f"<h1>Error</h1><p>{detail}</p><a href='/register_ui'>Back</a>"

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTML_LOGIN_PAGE

if __name__ == "__main__":
    import uvicorn
    # Run on 0.0.0.0:5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)