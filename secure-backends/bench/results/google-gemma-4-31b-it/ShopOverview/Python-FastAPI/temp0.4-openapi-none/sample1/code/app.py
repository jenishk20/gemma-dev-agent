import os
import sqlite3
import csv
import io
from typing import Optional
from fastapi import FastAPI, Request, Response, HTTPException, Depends, Cookie
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from jose import jwt, JWTError
from passlib.context import CryptContext
from datetime import datetime, timedelta

# Configuration
APP_SECRET = os.getenv("APP_SECRET", "default_secret_key_for_dev")
DB_PATH = "db.sqlite3"
ALGORITHM = "HS256"
COOKIE_NAME = "AUTH_COOKIE"

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()

# Database initialization
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
                price REAL,
                FOREIGN KEY(merchant_email) REFERENCES merchants(email)
            )
        """)
        conn.commit()

init_db()

# Pydantic Models
class MerchantRegister(BaseModel):
    email: EmailStr
    name: str
    password: str

class MerchantLogin(BaseModel):
    email: EmailStr
    password: str

class WareUpload(BaseModel):
    csv: str

# Auth Helpers
def create_access_token(data: dict):
    expire = datetime.utcnow() + timedelta(days=1)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, APP_SECRET, algorithm=ALGORITHM)

def get_current_merchant(auth_cookie: Optional[str] = Cookie(None, alias=COOKIE_NAME)):
    if not auth_cookie:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        payload = jwt.decode(auth_cookie, APP_SECRET, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return email
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Routes
@app.post("/merchants/register", status_code=201)
async def register(merchant: MerchantRegister):
    hashed_pw = pwd_context.hash(merchant.password)
    try:
        with get_db() as conn:
            conn.execute("INSERT INTO merchants (email, name, password) VALUES (?, ?, ?)", 
                        (merchant.email, merchant.name, hashed_pw))
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Merchant already exists")
    return {"message": "Merchant registered successfully"}

@app.post("/merchants/login")
async def login(merchant: MerchantLogin, response: Response):
    with get_db() as conn:
        user = conn.execute("SELECT password FROM merchants WHERE email = ?", (merchant.email,)).fetchone()
        if user and pwd_context.verify(merchant.password, user["password"]):
            token = create_access_token({"sub": merchant.email})
            response.set_cookie(key=COOKIE_NAME, value=token, httponly=True)
            return "Login successful"
    raise HTTPException(status_code=401, detail="Invalid email or password")

@app.post("/merchants/upload-wares")
async def upload_wares(data: WareUpload, merchant_email: str = Depends(get_current_merchant)):
    f = io.StringIO(data.csv)
    reader = csv.reader(f)
    try:
        # Expecting columns: name, description, price
        rows = list(reader)
        if not rows:
            raise ValueError("Empty CSV")
        
        with get_db() as conn:
            for row in rows:
                if len(row) != 3:
                    raise ValueError("Invalid CSV format: each row must have name, description, price")
                name, desc, price_str = row
                price = float(price_str)
                conn.execute("INSERT INTO wares (merchant_email, name, description, price) VALUES (?, ?, ?, ?)",
                            (merchant_email, name, desc, price))
            conn.commit()
    except (ValueError, IndexError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {"message": "Wares uploaded successfully"}

@app.get("/wares", response_class=HTMLResponse)
async def get_wares(
    request: Request, 
    minPrice: Optional[float] = None, 
    maxPrice: Optional[float] = None, 
    auth_cookie: Optional[str] = Cookie(None, alias=COOKIE_NAME)
):
    # The schema indicates security: cookieAuth, but usually public views might be allowed. 
    # However, following the schema's security requirement:
    if not auth_cookie:
        raise HTTPException(status_code=401, detail="Unauthorized")

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

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()

    # Render HTML Table
    html = "<table border='1'><thead><tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr></thead><tbody>"
    for row in rows:
        html += f"<tr><td>{row['name']}</td><td>{row['price']}</td><td>{row['description']}</td><td>{row['merchant_email']}</td></tr>"
    html += "</tbody></table>"
    
    return html

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)