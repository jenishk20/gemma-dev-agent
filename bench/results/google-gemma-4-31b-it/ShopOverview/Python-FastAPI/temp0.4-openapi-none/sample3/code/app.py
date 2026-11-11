import os
import sqlite3
import csv
import io
from typing import Optional
from fastapi import FastAPI, Request, Response, HTTPException, Depends, Cookie, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from jose import jwt, JWTException
from passlib.context import CryptContext
from jinja2 import Template

# Configuration
SECRET_KEY = os.getenv("APP_SECRET", "default_secret_key_for_dev")
ALGORITHM = "HS256"
DB_PATH = "db.sqlite3"

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
                merchant_email TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                FOREIGN KEY (merchant_email) REFERENCES merchants(email)
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

# Auth Utilities
def create_access_token(data: dict):
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def get_current_merchant(auth_cookie: Optional[str] = Cookie(None)):
    if not auth_cookie:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        payload = jwt.decode(auth_cookie, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTException:
        raise HTTPException(status_code=401, detail="Invalid session")

# Routes
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
        raise HTTPException(status_code=400, detail="Merchant already exists")
    return {"message": "Merchant registered successfully"}

@app.post("/merchants/login")
async def login(merchant: MerchantLogin):
    with get_db() as conn:
        user = conn.execute("SELECT * FROM merchants WHERE email = ?", (merchant.email,)).fetchone()
        if not user or not pwd_context.verify(merchant.password, user["password"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token({"sub": merchant.email})
    response = Response(content="Login successful", media_type="application/json")
    response.set_cookie(key="AUTH_COOKIE", value=token, httponly=True)
    return response

@app.post("/merchants/upload-wares")
async def upload_wares(upload: WareUpload, merchant_email: str = Depends(get_current_merchant)):
    f = io.StringIO(upload.csv)
    reader = csv.reader(f)
    
    try:
        rows = list(reader)
        if not rows:
            raise ValueError("Empty CSV")
            
        with get_db() as conn:
            for row in rows:
                if len(row) != 3:
                    raise ValueError("Invalid CSV format: expected 3 columns")
                name, description, price_str = row
                price = float(price_str)
                conn.execute(
                    "INSERT INTO wares (merchant_email, name, description, price) VALUES (?, ?, ?, ?)",
                    (merchant_email, name, description, price)
                )
            conn.commit()
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid CSV format or data types")
        
    return {"message": "Wares uploaded successfully"}

@app.get("/wares", response_class=HTMLResponse)
async def get_wares(
    request: Request, 
    minPrice: Optional[float] = None, 
    maxPrice: Optional[float] = None, 
    auth_cookie: Optional[str] = Cookie(None)
):
    # The schema specifies security: cookieAuth for this endpoint
    if not auth_cookie:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        jwt.decode(auth_cookie, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTException:
        raise HTTPException(status_code=401, detail="Invalid session")

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
        wares = conn.execute(query, params).fetchall()

    # Render HTML Table
    template = Template("""
    <html>
    <head><title>Warehouse</title></head>
    <body>
        <h1>Offered Wares</h1>
        <table border="1">
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
    
    return template.render(wares=wares)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)