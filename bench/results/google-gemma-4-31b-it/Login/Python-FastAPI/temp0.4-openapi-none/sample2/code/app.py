import os
import sqlite3
import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, EmailStr
from jose import JWTError, jwt
from passlib.context import CryptContext
from starlette.templating import Jinja2Templates

# Configuration
APP_SECRET = os.getenv("APP_SECRET", "default_secret_key_for_dev")
DB_PATH = "db.sqlite3"
ALGORITHM = "HS256"

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="LoginAPI")
templates = Jinja2Templates(directory=".") # We'll use inline templates via strings or simple HTML

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

# Utility functions
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, APP_SECRET, algorithm=ALGORITHM)

# HTML Templates (since we must keep everything in one file)
HTML_LOGIN = """
<!DOCTYPE html>
<html>
<head><title>Login</title></head>
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
<html>
<head><title>Register</title></head>
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
    hashed_password = pwd_context.hash(user.password)
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO users (email, password, name) VALUES (?, ?, ?)",
                (user.email, hashed_password, user.name)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email already in use or invalid data"
        )
    return {"message": "Registration successful"}

@app.post("/login", responses={200: TokenResponse, 401: MessageResponse})
async def login(user: LoginRequest):
    with get_db() as conn:
        cursor = conn.execute("SELECT password FROM users WHERE email = ?", (user.email,))
        row = cursor.fetchone()
        
    if not row or not pwd_context.verify(user.password, row['password']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid email or password"
        )
    
    token = create_access_token(data={"sub": user.email})
    return {"token": token, "message": "Login successful"}

# UI Endpoints (for the webapp part)
@app.get("/login_ui", response_class=HTMLResponse)
async def login_page():
    return HTML_LOGIN

@app.post("/login_ui")
async def login_ui_post(request: Request):
    form_data = await request.form()
    email = form_data.get("email")
    password = form_data.get("password")
    try:
        # Reusing the logic from the API endpoint
        res = await login(LoginRequest(email=email, password=password))
        return HTMLResponse(f"<h1>Login Successful</h1><p>Token: {res['token']}</p><a href='/login_ui'>Back</a>")
    except HTTPException as e:
        return HTMLResponse(f"<h1>Error</h1><p>{e.detail}</p><a href='/login_ui'>Back</a>", status_code=e.status_code)

@app.get("/register_ui", response_class=HTMLResponse)
async def register_page():
    return HTML_REGISTER

@app.post("/register_ui")
async def register_ui_post(request: Request):
    form_data = await request.form()
    email = form_data.get("email")
    password = form_data.get("password")
    name = form_data.get("name")
    try:
        # Reusing the logic from the API endpoint
        await register(RegisterRequest(email=email, password=password, name=name))
        return HTMLResponse("<h1>Registration Successful</h1><p>You can now <a href='/login_ui'>Login</a></p>")
    except HTTPException as e:
        return HTMLResponse(f"<h1>Error</h1><p>{e.detail}</p><a href='/register_ui'>Back</a>", status_code=e.status_code)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)