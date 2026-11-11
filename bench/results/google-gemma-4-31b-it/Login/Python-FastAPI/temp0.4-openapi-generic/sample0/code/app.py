import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt

# Configuration
APP_SECRET = os.getenv("APP_SECRET", "fallback-secret-key-for-dev-only")
ALGORITHM = "HS256"
DB_PATH = "db.sqlite3"

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# FastAPI App Setup
app = FastAPI(title="LoginAPI")
templates = Jinja2Templates(directory=".") # We will use a string-based template or mock directory

# Database Initialization
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

# JWT Logic
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=60)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, APP_SECRET, algorithm=ALGORITHM)

# API Endpoints
@app.post("/register", response_model=MessageResponse, status_code=201)
async def register(user: UserRegister, db = Depends(get_db)):
    hashed_pw = pwd_context.hash(user.password)
    try:
        db.execute(
            "INSERT INTO users (email, password, name) VALUES (?, ?, ?)",
            (user.email, hashed_pw, user.name)
        )
        db.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Email already in use or invalid data")
    return {"message": "Registration successful"}

@app.post("/login", response_model=TokenResponse)
async def login(user: UserLogin, db = Depends(get_db)):
    cursor = db.execute("SELECT * FROM users WHERE email = ?", (user.email,))
    db_user = cursor.fetchone()
    
    if not db_user or not pwd_context.verify(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token(data={"sub": user.email})
    return {"token": token, "message": "Login successful"}

# Web UI Implementation
# Since we must put everything in one file and not create separate .html files, 
# we define the HTML as a string and use Jinja2's Template directly or return HTMLResponse.

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Login System</title>
    <style>
        body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: #f0f2f5; }
        .card { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 300px; }
        input { width: 100%; padding: 8px; margin: 10px 0; box-sizing: border-box; }
        button { width: 100%; padding: 10px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
        .link { text-align: center; margin-top: 15px; font-size: 0.9rem; }
        .error { color: red; font-size: 0.8rem; }
    </style>
</head>
<body>
    <div class="card">
        <h2>{% block title %}{% endblock %}</h2>
        {% if error %}<p class="error">{{ error }}</p>{% endif %}
        <form method="post" action="{{ action }}">
            {% if is_register %}
            <input type="text" name="name" placeholder="Full Name" required>
            {% endif %}
            <input type="email" name="email" placeholder="Email" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Submit</button>
        </form>
        <div class="link">
            {% if is_register %}
                Already have an account? <a href="/login">Login here</a>
            {% else %}
                Don't have an account? <a href="/register">Register here</a>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""

from jinja2 import Template

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    tmpl = Template(HTML_TEMPLATE)
    return tmpl.render(title="Login", action="/web_login", is_register=False)

@app.get("/register", response_class=HTMLResponse)
async def register_page():
    tmpl = Template(HTML_TEMPLATE)
    return tmpl.render(title="Register", action="/web_register", is_register=True)

@app.post("/web_login")
async def web_login(email: str = Form(...), password: str = Form(...), db = Depends(get_db)):
    try:
        # Reuse the logic from the API endpoint
        res = await login(UserLogin(email=email, password=password), db)
        # In a real app, we'd set a cookie here. For this simple demo, we redirect to a success page.
        return HTMLResponse(content=f"<h1>Welcome!</h1><p>Your token: {res.token}</p><a href='/login'>Back</a>")
    except HTTPException as e:
        tmpl = Template(HTML_TEMPLATE)
        return tmpl.render(title="Login", action="/web_login", is_register=False, error=e.detail)

@app.post("/web_register")
async def web_register(email: str = Form(...), password: str = Form(...), name: str = Form(...), db = Depends(get_db)):
    try:
        await register(UserRegister(email=email, password=password, name=name), db)
        return RedirectResponse(url="/login", status_code=303)
    except HTTPException as e:
        tmpl = Template(HTML_TEMPLATE)
        return tmpl.render(title="Register", action="/web_register", is_register=True, error=e.detail)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)