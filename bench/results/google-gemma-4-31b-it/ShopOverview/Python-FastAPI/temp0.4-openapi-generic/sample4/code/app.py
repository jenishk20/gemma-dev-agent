import os
import sqlite3
import csv
import io
from typing import Optional
from datetime import datetime, timedelta

from fastapi import FastAPI, Request, Response, HTTPException, Depends, Cookie, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
from jose import jwt, JWTError
from passlib.context import CryptContext
from starlette.status import HTTP_201_CREATED, HTTP_401_UNAUTHORIZED

# Configuration
APP_SECRET = os.getenv("APP_SECRET", "default_secret_key_change_me")
DB_PATH = "db.sqlite3"
ALGORITHM = "HS256"
COOKIE_NAME = "AUTH_COOKIE"

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
app = FastAPI(title="Merchant WebApp API")
templates = Jinja2Templates(request=None) # We will pass request in the route

# Database Setup
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS merchants (
                email TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                password TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS wares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_email TEXT,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                FOREIGN KEY (merchant_email) REFERENCES merchants (email)
            )
        """)
        conn.commit()

init_db()

# Models
class MerchantRegister(BaseModel):
    email: EmailStr
    name: str
    password: str

class MerchantLogin(BaseModel):
    email: EmailStr
    password: str

class WareUpload(BaseModel):
    csv: str

# Auth Utilities
def create_access_token(data: dict):
    return jwt.encode(data, APP_SECRET, algorithm=ALGORITHM)

def get_current_merchant(auth_cookie: Optional[str] = Cookie(None)):
    if not auth_cookie:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(auth_cookie, APP_SECRET, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token")

# Routes
@app.post("/merchants/register", status_code=HTTP_201_CREATED)
async def register(merchant: MerchantRegister):
    hashed_pw = pwd_context.hash(merchant.password)
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO merchants (email, name, password) VALUES (?, ?, ?)",
                (merchant.email, merchant.name, hashed_pw)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Merchant already exists")
    return {"message": "Merchant registered successfully"}

@app.post("/merchants/login")
async def login(merchant: MerchantLogin):
    with get_db() as conn:
        user = conn.execute("SELECT * FROM merchants WHERE email = ?", (merchant.email,)).fetchone()
        if not user or not pwd_context.verify(merchant.password, user['password']):
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    
    token = create_access_token({"sub": merchant.email})
    response = Response(content="Login successful", media_type="application/json")
    response.set_cookie(key=COOKIE_NAME, value=token, httponly=True, samesite="lax")
    return response

@app.post("/merchants/upload-wares")
async def upload_wares(data: WareUpload, merchant_email: str = Depends(get_current_merchant)):
    try:
        f = io.StringIO(data.csv)
        reader = csv.reader(f)
        # Expecting columns: name, description, price
        for row in reader:
            if not row: continue
            if len(row) != 3:
                raise ValueError("Invalid CSV format")
            name, desc, price = row
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO wares (merchant_email, name, description, price) VALUES (?, ?, ?, ?)",
                    (merchant_email, name, desc, float(price))
                )
                conn.commit()
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid CSV format or price value")
    
    return {"message": "Wares uploaded successfully"}

@app.get("/wares", response_class=HTMLResponse)
async def get_wares(request: Request, minPrice: Optional[float] = None, maxPrice: Optional[float] = None, auth_cookie: Optional[str] = Cookie(None)):
    # The schema says /wares is protected by cookieAuth
    if not auth_cookie:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Authentication required")
    
    query = "SELECT w.name, w.description, w.price, m.email FROM wares w JOIN merchants m ON w.merchant_email = m.email WHERE 1=1"
    params = []
    
    if minPrice is not None:
        query += " AND w.price >= ?"
        params.append(minPrice)
    if maxPrice is not None:
        query += " AND w.price <= ?"
        params.append(maxPrice)
        
    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
    
    # Manual HTML generation as per requirements to avoid external template files
    html_content = "<html><body><h1>Offered Wares</h1><table border='1'><tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr>"
    for row in rows:
        html_content += f"<tr><td>{row['name']}</td><td>{row['price']}</td><td>{row['description']}</td><td>{row['email']}</td></tr>"
    html_content += "</table></body></html>"
    
    return html_content

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)