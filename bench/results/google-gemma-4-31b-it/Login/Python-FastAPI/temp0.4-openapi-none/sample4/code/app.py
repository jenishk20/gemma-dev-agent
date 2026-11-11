import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
from jose import JWTError, jwt
from passlib.context import CryptContext
from starlette.templating import Jinja2Templates

# Configuration
APP_SECRET = os.getenv("APP_SECRET", "fallback-secret-key-for-dev-only")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
DB_NAME = "db.sqlite3"

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="LoginAPI")
templates = Jinja2Templates(directory="templates") # We will use a trick to handle templates in one file

# Database helper
def get_db_connection():
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
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, APP_SECRET, algorithm=ALGORITHM)

# HTML Templates as strings (since we must stay in one file)
# We override the template loading by creating a custom directory or using a simple string response
# However, the prompt asks for a webapp. I'll provide the API endpoints and a simple HTML frontend 
# served via a route that returns HTMLResponse.

HTML_LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head><title>Login</title></head>
<body>
    <h2>Login</h2>
    <form action="/login" method="post">
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
<html>
<head><title>Register</title></head>
<body>
    <h2>Register</h2>
    <form action="/register" method="post">
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
    hashed_password = pwd_context.hash(user.password)
    try:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO users (email, password, name) VALUES (?, ?, ?)",
                (user.email, hashed_password, user.name)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Email already in use or invalid data")
    
    return {"message": "Registration successful"}

@app.post("/login", response_model=TokenResponse)
async def login(user: UserLogin):
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT password FROM users WHERE email = ?", (user.email,))
        row = cursor.fetchone()
        
        if not row or not pwd_context.verify(user.password, row['password']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid email or password"
            )
            
    token = create_access_token(data={"sub": user.email})
    return {"token": token, "message": "Login successful"}

# Frontend Routes (for the "webapp" part)
@app.get("/login_page", response_class=HTMLResponse)
async def login_page():
    return HTML_LOGIN_PAGE

@app.get("/register_page", response_class=HTMLResponse)
async def register_page():
    return HTML_REGISTER_PAGE

# To make the HTML forms work with the JSON API, we can add form-handling routes 
# or just rely on the API. Since the prompt asks for a webapp implementing the schema, 
# the API is the priority. I'll add a simple redirect/handler for the HTML forms.

from fastapi import Form

@app.post("/login_form", response_class=HTMLResponse)
async def login_form_handler(email: str = Form(...), password: str = Form(...)):
    try:
        # Call the logic of the login endpoint
        res = await login(UserLogin(email=email, password=password))
        return f"<h1>Login Successful</h1><p>Token: {res.token}</p>"
    except HTTPException as e:
        return f"<h1>Error</h1><p>{e.detail}</p><a href='/login_page'>Back</a>"

@app.post("/register_form", response_class=HTMLResponse)
async def register_form_handler(name: str = Form(...), email: str = Form(...), password: str = Form(...)):
    try:
        # Call the logic of the register endpoint
        await register(UserRegister(email=email, password=password, name=name))
        return "<h1>Registration Successful</h1><p><a href='/login_page'>Login now</a></p>"
    except HTTPException as e:
        return f"<h1>Error</h1><p>{e.detail}</p><a href='/register_page'>Back</a>"

# Update HTML forms to point to these handlers
HTML_LOGIN_PAGE = HTML_LOGIN_PAGE.replace('action="/login"', 'action="/login_form"')
HTML_REGISTER_PAGE = HTML_REGISTER_PAGE.replace('action="/register"', 'action="/register_form"')

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)