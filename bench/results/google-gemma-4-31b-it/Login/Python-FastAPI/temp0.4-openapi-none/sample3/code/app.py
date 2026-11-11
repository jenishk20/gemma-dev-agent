import os
import sqlite3
import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from jose import jwt
from passlib.context import CryptContext
from fastapi.templating import Jinja2Templates
from starlette.templating import TemplateResponse

# Configuration
APP_SECRET = os.getenv("APP_SECRET", "default_secret_key_for_dev")
ALGORITHM = "HS256"
DB_PATH = "db.sqlite3"

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="LoginAPI")
templates = Jinja2Templates(dirname=".") # We will use inline templates via strings for simplicity in a single file, but Jinja2 is available.

# Database Setup
def get_db_connection():
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

# Pydantic Models
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
    expire = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, APP_SECRET, algorithm=ALGORITHM)

# HTML Templates (Stored as strings since we must keep everything in one file)
HTML_LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
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
<html>
<head>
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
    hashed_pw = pwd_context.hash(user.password)
    try:
        with get_db_connection() as conn:
            conn.execute("INSERT INTO users (email, password, name) VALUES (?, ?, ?)", 
                         (user.email, hashed_pw, user.name))
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Email already in use or invalid data")
    return {"message": "Registration successful"}

@app.post("/login", response_model=LoginResponse)
async def login(user: LoginRequest):
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT password FROM users WHERE email = ?", (user.email,))
        row = cursor.fetchone()
        
    if row and pwd_context.verify(user.password, row['password']):
        token = create_access_token({"sub": user.email})
        return {"token": token, "message": "Login successful"}
    
    raise HTTPException(status_code=401, detail="Invalid email or password")

# UI Endpoints (for the "webapp" part)
@app.get("/login_ui", response_class=HTMLResponse)
async def get_login_page():
    return HTML_LOGIN_PAGE

@app.post("/login_ui", response_class=HTMLResponse)
async def post_login_page(request: Request):
    form_data = await request.form()
    email = form_data.get("email")
    password = form_data.get("password")
    
    try:
        # Reuse the API logic
        res = await login(LoginRequest(email=email, password=password))
        return f"<h1>Welcome!</h1><p>Login successful. Your token is: {res.token}</p>"
    except HTTPException as e:
        return f"<h1>Error</h1><p>{e.detail}</p><a href='/login_ui'>Back</a>"

@app.get("/register_ui", response_class=HTMLResponse)
async def get_register_page():
    return HTML_REGISTER_PAGE

@app.post("/register_ui", response_class=HTMLResponse)
async def post_register_page(request: Request):
    form_data = await request.form()
    name = form_data.get("name")
    email = form_data.get("email")
    password = form_data.get("password")
    
    try:
        await register(RegisterRequest(email=email, password=password, name=name))
        return "<h1>Success!</h1><p>Registration successful. <a href='/login_ui'>Login now</a></p>"
    except HTTPException as e:
        return f"<h1>Error</h1><p>{e.detail}</p><a href='/register_ui'>Back</a>"

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTML_LOGIN_PAGE

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)