import os
import sqlite3
import csv
import io
from typing import Optional
from datetime import datetime, timedelta

from fastapi import FastAPI, Request, Response, HTTPException, Depends, status, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
from jose import JWTError, jwt
from passlib.context import CryptContext

# Configuration
APP_SECRET = os.getenv("APP_SECRET", "default_secret_key_for_development")
ALGORITHM = "HS256"
DB_FILE = "db.sqlite3"

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="Merchant WebApp API")
templates = Jinja2Templates(directory=".") # We will use inline templates or simple strings

# Database Setup
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
            CREATE TABLE IF NOT EXISTS merchants (
                email TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                password TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS wares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_email TEXT NOT NULL,
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
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, APP_SECRET, algorithm=ALGORITHM)

def get_current_merchant(request: Request):
    token = request.cookies.get("AUTH_COOKIE")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(token, APP_SECRET, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

# Routes
@app.post("/merchants/register", status_code=201)
async def register(merchant: MerchantRegister):
    hashed_pw = pwd_context.hash(merchant.password)
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute(
                "INSERT INTO merchants (email, name, password) VALUES (?, ?, ?)",
                (merchant.email, merchant.name, hashed_pw)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Merchant with this email already exists")
    return None

@app.post("/merchants/login")
async def login(merchant: MerchantLogin):
    with sqlite3.connect(DB_FILE) as conn:
        user = conn.execute("SELECT password FROM merchants WHERE email = ?", (merchant.email,)).fetchone()
        if not user or not pwd_context.verify(merchant.password, user[0]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token(data={"sub": merchant.email})
    response = Response(content="Login successful", media_type="application/json")
    response.set_cookie(key="AUTH_COOKIE", value=token, httponly=True, samesite="lax")
    return response

@app.post("/merchants/upload-wares")
async def upload_wares(data: WareUpload, merchant_email: str = Depends(get_current_merchant)):
    try:
        f = io.StringIO(data.csv)
        reader = csv.reader(f)
        # Expecting columns: name, description, price
        rows = list(reader)
        
        with sqlite3.connect(DB_FILE) as conn:
            for row in rows:
                if len(row) != 3:
                    raise ValueError("Invalid CSV format")
                name, desc, price_str = row
                price = float(price_str)
                conn.execute(
                    "INSERT INTO wares (merchant_email, name, description, price) VALUES (?, ?, ?, ?)",
                    (merchant_email, name, desc, price)
                )
            conn.commit()
    except (ValueError, csv.Error):
        raise HTTPException(status_code=400, detail="Invalid CSV format")
    
    return {"message": "Wares uploaded successfully"}

@app.get("/wares", response_class=HTMLResponse)
async def get_wares(
    request: Request, 
    minPrice: Optional[float] = None, 
    maxPrice: Optional[float] = None, 
    merchant_email: str = Depends(get_current_merchant)
):
    query = "SELECT w.name, w.price, w.description, w.merchant_email FROM wares w"
    params = []
    conditions = []

    if minPrice is not None:
        conditions.append("w.price >= ?")
        params.append(minPrice)
    if maxPrice is not None:
        conditions.append("w.price <= ?")
        params.append(maxPrice)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params).fetchall()

    # Simple HTML Table Generation
    html_content = "<html><body><h1>Offered Wares</h1><table border='1'><tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr>"
    for row in rows:
        html_content += f"<tr><td>{row['name']}</td><td>{row['price']}</td><td>{row['description']}</td><td>{row['merchant_email']}</td></tr>"
    html_content += "</table></body></html>"
    
    return html_content

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)