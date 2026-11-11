import os
import sqlite3
import csv
import io
from typing import Optional
from datetime import datetime, timedelta

from fastapi import FastAPI, Request, Response, HTTPException, Depends, status, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from jose import JWTError, jwt
from passlib.context import CryptContext
from jinja2 import Template

# Configuration
APP_SECRET = os.getenv("APP_SECRET", "default_secret_key_for_development")
ALGORITHM = "HS256"
DB_PATH = "db.sqlite3"

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="Merchant WebApp API")

# Database Setup
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
    return jwt.encode(to_encode, APP_SECRET, algorithm=ALGORITHM)

def get_current_merchant_id(request: Request):
    token = request.cookies.get("AUTH_COOKIE")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(token, APP_SECRET, algorithms=[ALGORITHM])
        merchant_id: int = payload.get("sub")
        if merchant_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return merchant_id
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

# HTML Templates
WARE_TABLE_TEMPLATE = Template("""
<!DOCTYPE html>
<html>
<head>
    <title>Warehouse</title>
    <style>
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        tr:nth-child(even){background-color: #f2f2f2;}
        th { background-color: #4CAF50; color: white; }
    </style>
</head>
<body>
    <h1>Offered Wares</h1>
    <table>
        <thead>
            <tr>
                <th>Name</th>
                <th>Price</th>
                <th>Description</th>
                <th>Merchant Email</th>
            </tr>
        </thead>
        <tbody>
            {% for ware in wares %}
            <tr>
                <td>{{ ware.name }}</td>
                <td>{{ ware.price }}</td>
                <td>{{ ware.description }}</td>
                <td>{{ ware.merchant_email }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</body>
</html>
""")

# Routes
@app.post("/merchants/register", status_code=201)
def register(merchant: MerchantRegister):
    hashed_pw = pwd_context.hash(merchant.password)
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO merchants (email, name, password) VALUES (?, ?, ?)",
                (merchant.email, merchant.name, hashed_pw)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Email already registered")
    return {"message": "Merchant registered successfully"}

@app.post("/merchants/login")
def login(merchant: MerchantLogin):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        user = conn.execute("SELECT * FROM merchants WHERE email = ?", (merchant.email,)).fetchone()
    
    if not user or not pwd_context.verify(merchant.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token({"sub": str(user["id"])})
    response = Response(content="Login successful", media_type="application/json")
    response.set_cookie(key="AUTH_COOKIE", value=token, httponly=True)
    return response

@app.post("/merchants/upload-wares")
def upload_wares(payload: WareUpload, merchant_id: int = Depends(get_current_merchant_id)):
    try:
        f = io.StringIO(payload.csv)
        reader = csv.reader(f)
        # Expecting: name, description, price
        rows = list(reader)
        
        with sqlite3.connect(DB_PATH) as conn:
            for row in rows:
                if len(row) != 3:
                    raise ValueError("Invalid column count")
                name, desc, price = row
                conn.execute(
                    "INSERT INTO wares (merchant_id, name, description, price) VALUES (?, ?, ?, ?)",
                    (merchant_id, name, desc, float(price))
                )
            conn.commit()
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid CSV format")
    
    return {"message": "Wares uploaded successfully"}

@app.get("/wares", response_class=HTMLResponse)
def get_wares(
    request: Request, 
    minPrice: Optional[float] = None, 
    maxPrice: Optional[float] = None, 
    merchant_id: int = Depends(get_current_merchant_id)
):
    query = """
        SELECT w.name, w.price, w.description, m.email as merchant_email 
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
    
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params).fetchall()
    
    wares_list = [dict(row) for row in rows]
    return WARE_TABLE_TEMPLATE.render(wares=wares_list)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)