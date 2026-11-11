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
DB_PATH = "db.sqlite3"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="LoginAPI")
templates = Jinja2Templates(directory=".") # Using current dir for templates in single-file setup

# Database initialization
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

init_db()

# Pydantic Models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    token: str
    message: str

class MessageResponse(BaseModel):
    message: str

# Utility functions
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, APP_SECRET, algorithm=ALGORITHM)

# HTML Templates (embedded as strings for single-file requirement)
# Since Jinja2Templates expects a directory, we will override the response 
# to serve HTML directly for the login page.
LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Login Page</title>
    <style>
        body { font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background-color: #f0f2f5; }
        .container { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 300px; }
        input { width: 100%; padding: 8px; margin: 10px 0; box-sizing: border-box; }
        button { width: 100%; padding: 10px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
        .toggle { text-align: center; margin-top: 15px; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="container">
        <h2 id="title">Login</h2>
        <form id="authForm">
            <input type="text" id="name" placeholder="Full Name" style="display:none">
            <input type="email" id="email" placeholder="Email" required>
            <input type="password" id="password" placeholder="Password" required>
            <button type="submit" id="btn">Login</button>
        </form>
        <div class="toggle">
            <a href="#" id="toggleLink" onclick="toggleMode()">Need an account? Register</a>
        </div>
        <p id="msg" style="color: red; font-size: 0.8em; text-align: center;"></p>
    </div>
    <script>
        let isLogin = true;
        function toggleMode() {
            isLogin = !isLogin;
            document.getElementById('title').innerText = isLogin ? 'Login' : 'Register';
            document.getElementById('btn').innerText = isLogin ? 'Login' : 'Register';
            document.getElementById('name').style.display = isLogin ? 'none' : 'block';
            document.getElementById('toggleLink').innerText = isLogin ? 'Need an account? Register' : 'Have an account? Login';
        }
        document.getElementById('authForm').onsubmit = async (e) => {
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
                document.getElementById('msg').style.color = 'green';
                document.getElementById('msg').innerText = isLogin ? 'Login successful! Token: ' + data.token : 'Registration successful! Please login.';
                if (!isLogin) toggleMode();
            } else {
                document.getElementById('msg').style.color = 'red';
                document.getElementById('msg').innerText = data.message;
            }
        };
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def get_login_page():
    return LOGIN_HTML

@app.post("/register", status_code=status.HTTP_201_CREATED, response_model=MessageResponse)
def register(user: UserRegister, db=Depends(get_db)):
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
        raise HTTPException(status_code=400, detail="Registration failed")
    
    return {"message": "Registration successful"}

@app.post("/login", response_model=TokenResponse)
def login(user: UserLogin, db=Depends(get_db)):
    cursor = db.execute("SELECT password FROM users WHERE email = ?", (user.email,))
    row = cursor.fetchone()
    
    if not row or not pwd_context.verify(user.password, row['password']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid email or password"
        )
    
    token = create_access_token(data={"sub": user.email})
    return {"token": token, "message": "Login successful"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)