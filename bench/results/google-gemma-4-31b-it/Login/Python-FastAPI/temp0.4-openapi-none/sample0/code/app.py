import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from jose import JWTError, jwt
from passlib.context import CryptContext
from jinja2 import Template

# Configuration
APP_SECRET = os.getenv("APP_SECRET", "default_secret_key_for_development")
DB_PATH = "db.sqlite3"
ALGORITHM = "HS256"

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Database Setup
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
                password TEXT NOT NULL,
                name TEXT NOT NULL
            )
        """)
        conn.commit()

init_db()

# Pydantic Models
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    token: str
    message: str

# FastAPI App
app = FastAPI(title="LoginAPI")

# HTML Templates (Embedded)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Login System</title>
    <style>
        body { font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background-color: #f0f2f5; }
        .container { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 300px; }
        h2 { text-align: center; color: #333; }
        input { width: 100%; padding: 10px; margin: 10px 0; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; }
        button { width: 100%; padding: 10px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background: #0056b3; }
        .link { text-align: center; margin-top: 15px; font-size: 0.9rem; }
        .error { color: red; font-size: 0.8rem; text-align: center; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="container">
        {% if page == 'login' %}
            <h2>Login</h2>
            <form action="/login_submit" method="post">
                <input type="email" name="email" placeholder="Email" required>
                <input type="password" name="password" placeholder="Password" required>
                <button type="submit">Login</button>
            </form>
            <div class="link">Don't have an account? <a href="/register">Register here</a></div>
        {% else %}
            <h2>Register</h2>
            <form action="/register_submit" method="post">
                <input type="text" name="name" placeholder="Full Name" required>
                <input type="email" name="email" placeholder="Email" required>
                <input type="password" name="password" placeholder="Password" required>
                <button type="submit">Sign Up</button>
            </form>
            <div class="link">Already have an account? <a href="/">Login here</a></div>
        {% endif %}
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
    </div>
</body>
</html>
"""
template = Template(HTML_TEMPLATE)

# Helper for JWT
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=60)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, APP_SECRET, algorithm=ALGORITHM)

# API Endpoints
@app.post("/register", status_code=status.HTTP_201_CREATED, responses={201: {"description": "Successful registration"}, 400: {"description": "Bad Request"}})
async def register(user: RegisterRequest):
    hashed_password = pwd_context.hash(user.password)
    try:
        with get_db() as conn:
            conn.execute("INSERT INTO users (email, password, name) VALUES (?, ?, ?)", 
                         (user.email, hashed_password, user.name))
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Email already in use or invalid data")
    
    return {"message": "Registration successful"}

@app.post("/login", responses={200: {"description": "Successful login"}, 401: {"description": "Unauthorized"}})
async def login(user: LoginRequest):
    with get_db() as conn:
        cursor = conn.execute("SELECT password FROM users WHERE email = ?", (user.email,))
        row = cursor.fetchone()
        
    if not row or not pwd_context.verify(user.password, row['password']):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token(data={"sub": user.email})
    return {"token": token, "message": "Login successful"}

# Web UI Endpoints
@app.get("/", response_class=HTMLResponse)
async def index():
    return template.render(page='login')

@app.get("/register", response_class=HTMLResponse)
async def register_page():
    return template.render(page='register')

@app.post("/register_submit", response_class=HTMLResponse)
async def register_submit(request: Request):
    form_data = await request.form()
    try:
        reg_data = RegisterRequest(
            email=form_data.get("email"),
            password=form_data.get("password"),
            name=form_data.get("name")
        )
        await register(reg_data)
        return HTMLResponse(content="<script>alert('Registration successful!'); window.location.href='/';</script>")
    except Exception as e:
        error_msg = str(e)
        return template.render(page='register', error=error_msg)

@app.post("/login_submit", response_class=HTMLResponse)
async def login_submit(request: Request):
    form_data = await request.form()
    try:
        log_data = LoginRequest(
            email=form_data.get("email"),
            password=form_data.get("password")
        )
        res = await login(log_data)
        # In a real app, we'd set a cookie here
        return HTMLResponse(content=f"<script>alert('Login successful! Token: {res['token']}'); window.location.href='/';</script>")
    except HTTPException as e:
        return template.render(page='login', error=e.detail)
    except Exception as e:
        return template.render(page='login', error="An unexpected error occurred")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)