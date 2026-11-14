import os
import sqlite3
import csv
import io
from typing import Optional
from fastapi import FastAPI, Request, Response, HTTPException, Depends, Cookie, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from jose import jwt, JWTError
from passlib.context import CryptContext
from datetime import datetime, timedelta

# Configuration
SECRET_KEY = os.getenv("APP_SECRET", "default_secret_key_for_development")
ALGORITHM = "HS256"
DB_NAME = "db.sqlite3"

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="Merchant WebApp API")

# Database Setup
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS merchants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                password TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS wares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                FOREIGN KEY (merchant_id) REFERENCES merchants(id)
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
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_merchant_id(AUTH_COOKIE: Optional[str] = Cookie(None)):
    if not AUTH_COOKIE:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        payload = jwt.decode(AUTH_COOKIE, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Endpoints
@app.post("/merchants/register", status_code=201)
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
        raise HTTPException(status_code=400, detail="Email already registered")
    return {"message": "Merchant registered successfully"}

@app.post("/merchants/login")
async def login(merchant: MerchantLogin):
    with get_db() as conn:
        user = conn.execute("SELECT id, password FROM merchants WHERE email = ?", (merchant.email,)).fetchone()
        if not user or not pwd_context.verify(merchant.password, user["password"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        token = create_access_token({"sub": str(user["id"])})
        response = Response(content="Login successful", media_type="application/json")
        response.set_cookie(key="AUTH_COOKIE", value=token, httponly=True)
        return response

@app.post("/merchants/upload-wares")
async def upload_wares(ware_data: WareUpload, merchant_id: str = Depends(get_current_merchant_id)):
    try:
        f = io.StringIO(ware_data.csv)
        reader = csv.DictReader(f)
        # Expected columns: name, description, price
        rows = list(reader)
        if not rows:
            raise HTTPException(status_code=400, detail="CSV is empty or invalid")
        
        with get_db() as conn:
            for row in rows:
                if not all(k in row for k in ("name", "description", "price")):
                    raise HTTPException(status_code=400, detail="Invalid CSV format: missing columns")
                conn.execute(
                    "INSERT INTO wares (merchant_id, name, description, price) VALUES (?, ?, ?, ?)",
                    (int(merchant_id), row["name"], row["description"], float(row["price"]))
                )
            conn.commit()
    except (ValueError, KeyError):
        raise HTTPException(status_code=400, detail="Invalid CSV data types")
    
    return {"message": "Wares uploaded successfully"}

@app.get("/wares", response_class=HTMLResponse)
async def get_wares(
    minPrice: Optional[float] = None, 
    maxPrice: Optional[float] = None, 
    merchant_id: str = Depends(get_current_merchant_id)
):
    query = """
        SELECT w.name, w.price, w.description, m.email 
        FROM wares w 
        JOIN merchants m ON w.merchant_id = m.id 
        WHERE 1=1
    """
    params = []
    if minPrice is not None:
        query += " AND w.price >= ?"
        params.append(minPrice)
    if maxPrice is not None:
        query += " AND w.price <= ?"
        params.append(maxPrice)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()

    html = "<table border='1'><tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr>"
    for row in rows:
        html += f"<tr><td>{row['name']}</td><td>{row['price']}</td><td>{row['description']}</td><td>{row['email']}</td></tr>"
    html += "</table>"
    
    return html

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)