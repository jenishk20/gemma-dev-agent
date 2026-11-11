import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
from jose import JWTClaimsPayload, jwt
from passlib.context import CryptContext

# Configuration
APP_SECRET = os.getenv("APP_SECRET", "default_secret_key_change_me_in_production")
ALGORITHM = "HS256"
DB_FILE = "db.sqlite3"

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="LoginAPI")
templates = Jinja2Templates(request=Request) # We will use a string for templates to keep it in one file

# Database setup
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
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

# Helpers
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=60)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, APP_SECRET, algorithm=ALGORITHM)

# HTML Templates (Embedded as strings for single-file requirement)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Login/Register</title>
    <style>
        body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: #f0f2f5; }
        .card { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 300px; }
        input { width: 100%; padding: 8px; margin: 10px 0; box-sizing: border-box; }
        button { width: 100%; padding: 10px; background: #007bff; color: white; border: none; cursor: pointer; }
        .toggle { margin-top: 15px; text-align: center; font-size: 0.9em; cursor: pointer; color: blue; }
    </style>
</head>
<body>
    <div class="card">
        <h2 id="title">Login</h2>
        <form id="authForm">
            <input type="email" id="email" placeholder="Email" required>
            <input type="password" id="password" placeholder="Password" required>
            <input type="text" id="name" placeholder="Full Name" style="display:none">
            <button type="submit" id="submitBtn">Login</button>
        </form>
        <div class="toggle" id="toggleLink">Need an account? Register</div>
        <p id="msg" style="color: red; font-size: 0.8em;"></p>
    </div>

    <script>
        let isLogin = true;
        const form = document.getElementById('authForm');
        const title = document.getElementById('title');
        const nameInput = document.getElementById('name');
        const submitBtn = document.getElementById('submitBtn');
        const toggleLink = document.getElementById('toggleLink');
        const msg = document.getElementById('msg');

        toggleLink.onclick = () => {
            isLogin = !isLogin;
            title.innerText = isLogin ? 'Login' : 'Register';
            nameInput.style.display = isLogin ? 'none' : 'block';
            submitBtn.innerText = isLogin ? 'Login' : 'Register';
            toggleLink.innerText = isLogin ? 'Need an account? Register' : 'Have an account? Login';
            msg.innerText = '';
        };

        form.onsubmit = async (e) => {
            e.preventDefault();
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const name = document.getElementById('name').value;
            const endpoint = isLogin ? '/login' : '/register';
            const body = isLogin ? {email, password} : {email, password, name};

            const res = await fetch(endpoint, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(body)
            });
            const data = await res.json();
            if (res.ok) {
                msg.style.color = 'green';
                msg.innerText = isLogin ? 'Login successful! Token: ' + data.token : 'Registration successful! Please login.';
                if (!isLogin) toggleLink.click();
            } else {
                msg.style.color = 'red';
                msg.innerText = data.message || 'An error occurred';
            }
        };
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_TEMPLATE

@app.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def register(user: RegisterRequest, db: sqlite3.Connection = Depends(get_db)):
    # Check if user exists
    cursor = db.execute("SELECT id FROM users WHERE email = ?", (user.email,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Email already in use or invalid data")
    
    hashed_pw = pwd_context.hash(user.password)
    try:
        db.execute("INSERT INTO users (email, password, name) VALUES (?, ?, ?)", 
                  (user.email, hashed_pw, user.name))
        db.commit()
    except Exception:
        raise HTTPException(status_code=400, detail="Email already in use or invalid data")
    
    return {"message": "Registration successful"}

@app.post("/login", response_model=TokenResponse)
async def login(user: LoginRequest, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.execute("SELECT password FROM users WHERE email = ?", (user.email,))
    row = cursor.fetchone()
    
    if not row or not pwd_context.verify(user.password, row['password']):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token(data={"sub": user.email})
    return {"token": token, "message": "Login successful"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)