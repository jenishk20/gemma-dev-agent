import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr, Field
from passlib.context import CryptContext
from jose import JWTError, jwt

# Configuration
# Ensure APP_SECRET is handled securely. If not provided, we use a fallback but in production it must be set.
APP_SECRET = os.getenv("APP_SECRET", "fallback_secure_random_string_for_dev_only")
ALGORITHM = "HS256"
DB_PATH = "db.sqlite3"

# Password hashing setup: bcrypt is a strong salted KDF.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="LoginAPI")

# Database helper
def get_db_connection():
    # Use check_same_thread=False because FastAPI handles requests in threads/async
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
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

# Pydantic Models with constraints to prevent resource exhaustion (DoS via huge strings)
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=255)

class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)

class TokenResponse(BaseModel):
    token: str
    message: str

class MessageResponse(BaseModel):
    message: str

# JWT Utility
def create_access_token(data: dict):
    to_encode = data.copy()
    # Set expiry to prevent long-term token misuse
    expire = datetime.utcnow() + timedelta(minutes=60)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, APP_SECRET, algorithm=ALGORITHM)

# HTML Template
# Input is handled via JavaScript fetch and JSON, reducing XSS risk in the backend.
# The HTML is static and does not use server-side template interpolation of user input.
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Login Page</title>
    <style>
        body { font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: #f0f2f5; margin: 0; }
        .card { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 300px; }
        input { width: 100%; padding: 8px; margin: 10px 0; box-sizing: border-box; }
        button { width: 100%; padding: 10px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
        .toggle { font-size: 0.8rem; text-align: center; margin-top: 15px; cursor: pointer; color: #007bff; }
    </style>
</head>
<body>
    <div class="card" id="auth-card">
        <h2 id="title">Login</h2>
        <form id="auth-form">
            <input type="text" id="name" placeholder="Full Name" style="display:none;">
            <input type="email" id="email" placeholder="Email" required>
            <input type="password" id="password" placeholder="Password" required>
            <button type="submit" id="btn-text">Login</button>
        </form>
        <div class="toggle" id="toggle-link">Don't have an account? Register</div>
        <p id="msg" style="color: red; font-size: 0.8rem; text-align: center;"></p>
    </div>

    <script>
        let isLogin = true;
        const form = document.getElementById('auth-form');
        const title = document.getElementById('title');
        const nameInput = document.getElementById('name');
        const btnText = document.getElementById('btn-text');
        const toggleLink = document.getElementById('toggle-link');
        const msg = document.getElementById('msg');

        toggleLink.onclick = () => {
            isLogin = !isLogin;
            title.innerText = isLogin ? 'Login' : 'Register';
            nameInput.style.display = isLogin ? 'none' : 'block';
            btnText.innerText = isLogin ? 'Login' : 'Register';
            toggleLink.innerText = isLogin ? "Don't have an account? Register" : "Already have an account? Login";
            msg.innerText = '';
        };

        form.onsubmit = async (e) => {
            e.preventDefault();
            msg.innerText = '';
            const payload = {
                email: document.getElementById('email').value,
                password: document.getElementById('password').value,
            };
            if (!isLogin) payload.name = document.getElementById('name').value;

            const endpoint = isLogin ? '/login' : '/register';
            try {
                const res = await fetch(endpoint, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (res.ok) {
                    msg.style.color = 'green';
                    msg.innerText = isLogin ? `Success! Token: ${data.token}` : 'Registered! Please login.';
                    if (!isLogin) toggleLink.click();
                } else {
                    msg.style.color = 'red';
                    msg.innerText = data.detail || data.message || 'An error occurred';
                }
            } catch (err) {
                msg.style.color = 'red';
                msg.innerText = 'Network error occurred';
            }
        };
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_CONTENT

@app.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UserRegister):
    # Passlib bcrypt handles salting and constant-time comparison internally.
    hashed_pw = pwd_context.hash(user.password)
    try:
        with get_db_connection() as conn:
            # Using parameterized queries to prevent SQL Injection.
            conn.execute("INSERT INTO users (email, password, name) VALUES (?, ?, ?)", 
                        (user.email, hashed_pw, user.name))
            conn.commit()
    except sqlite3.IntegrityError:
        # Return the documented 400 error for duplicate emails.
        raise HTTPException(status_code=400, detail="Email already in use or invalid data")
    except Exception:
        # Generic error handling to prevent leaking internal stack traces.
        raise HTTPException(status_code=400, detail="An error occurred during registration")
    
    return {"message": "Registration successful"}

@app.post("/login", response_model=TokenResponse)
async def login(user: UserLogin):
    try:
        with get_db_connection() as conn:
            # Using parameterized queries to prevent SQL Injection.
            cursor = conn.execute("SELECT password FROM users WHERE email = ?", (user.email,))
            row = cursor.fetchone()
            
        # Verify password using bcrypt's constant-time comparison.
        if not row or not pwd_context.verify(user.password, row['password']):
            # Use a generic message for both "user not found" and "wrong password" to prevent account enumeration.
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        token = create_access_token(data={"sub": user.email})
        return {"token": token, "message": "Login successful"}
    except HTTPException:
        raise
    except Exception:
        # Generic error handling to prevent leaking internal stack traces.
        raise HTTPException(status_code=401, detail="Invalid email or password")

if __name__ == "__main__":
    import uvicorn
    # Run on 0.0.0.0:5000 as requested.
    uvicorn.run(app, host="0.0.0.0", port=5000)