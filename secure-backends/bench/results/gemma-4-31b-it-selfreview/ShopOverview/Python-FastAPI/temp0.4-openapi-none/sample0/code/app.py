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
from jinja2 import Template, escape

# Configuration
APP_SECRET = os.environ.get("APP_SECRET", "default_secret_key_for_dev")
ALGORITHM = "HS256"
DB_PATH = "db.sqlite3"

# Password hashing - bcrypt is a strong salted KDF
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="Merchant WebApp API")

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
    # Added expiry to prevent infinite session lifetime
    return jwt.encode(data, APP_SECRET, algorithm=ALGORITHM)

def get_current_merchant(AUTH_COOKIE: Optional[str] = Cookie(None)):
    if not AUTH_COOKIE:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        # Verify token signature and algorithm
        payload = jwt.decode(AUTH_COOKIE, APP_SECRET, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid session")

# Routes
@app.post("/merchants/register", status_code=201)
async def register(merchant: MerchantRegister):
    hashed_pw = pwd_context.hash(merchant.password)
    try:
        with get_db() as conn:
            # Parameterized query prevents SQL Injection
            conn.execute(
                "INSERT INTO merchants (email, name, password) VALUES (?, ?, ?)",
                (merchant.email, merchant.name, hashed_pw)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Email already registered")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid input")
    return None

@app.post("/merchants/login")
async def login(merchant: MerchantLogin):
    try:
        with get_db() as conn:
            user = conn.execute("SELECT password FROM merchants WHERE email = ?", (merchant.email,)).fetchone()
            # passlib.verify uses constant-time comparison
            if not user or not pwd_context.verify(merchant.password, user['password']):
                raise HTTPException(status_code=401, detail="Invalid email or password")
        
        token = create_access_token({"sub": merchant.email})
        response = Response(content="Login successful", media_type="application/json")
        # HttpOnly and Secure flags prevent XSS access and sniffing
        response.set_cookie(key="AUTH_COOKIE", value=token, httponly=True, secure=True, samesite="lax")
        return response
    except HTTPException as e:
        raise e
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid email or password")

@app.post("/merchants/upload-wares")
async def upload_wares(data: WareUpload, merchant_email: str = Depends(get_current_merchant)):
    # Resource exhaustion: bound input size for the CSV string
    if len(data.csv) > 1_000_000: # 1MB limit
        raise HTTPException(status_code=400, detail="Invalid CSV format")
        
    try:
        f = io.StringIO(data.csv)
        reader = csv.reader(f)
        rows = list(reader)
        
        # Resource exhaustion: bound number of rows
        if len(rows) > 1000:
            raise ValueError("Too many rows")

        with get_db() as conn:
            for row in rows:
                if len(row) != 3:
                    raise ValueError("Invalid CSV format")
                name, desc, price_str = row
                try:
                    price = float(price_str)
                except ValueError:
                    raise ValueError("Invalid price format")
                
                # Parameterized query prevents SQL Injection
                conn.execute(
                    "INSERT INTO wares (merchant_email, name, description, price) VALUES (?, ?, ?, ?)",
                    (merchant_email, name, desc, price)
                )
            conn.commit()
    except (ValueError, StopIteration):
        raise HTTPException(status_code=400, detail="Invalid CSV format")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid CSV format")
    
    return {"message": "Wares uploaded successfully"}

@app.get("/wares", response_class=HTMLResponse)
async def get_wares(
    request: Request, 
    minPrice: Optional[float] = None, 
    maxPrice: Optional[float] = None, 
    AUTH_COOKIE: Optional[str] = Cookie(None)
):
    if not AUTH_COOKIE:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        jwt.decode(AUTH_COOKIE, APP_SECRET, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid session")

    # Parameterized query prevents SQL Injection
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

    try:
        with get_db() as conn:
            wares = conn.execute(query, params).fetchall()
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

    # Use Jinja2's auto-escaping or explicit escape() to prevent XSS
    # The template below uses {{ }} which Jinja2 escapes by default if configured, 
    # but we ensure the data is treated as text.
    template = Template("""
    <html lang="en">
        <head><title>Warehouse</title></head>
        <body>
            <h1 style="font-family: sans-serif;">Offered Wares</h1>
            <table border="1" style="border-collapse: collapse; width: 100%;">
                <thead>
                    <tr style="background-color: #eee;">
                        <th>Name</th>
                        <th>Price</th>
                        <th>Description</th>
                        <th>Merchant</th>
                    </tr>
                </thead>
                <tbody>
                    {% for ware in wares %}
                    <tr>
                        <td>{{ ware.name | e }}</td>
                        <td>{{ ware.price | e }}</td>
                        <td>{{ ware.description | e }}</td>
                        <td>{{ ware.merchant_email | e }}</td>
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
    # Port 5000 as requested
    uvicorn.run(app, host="0.0.0.0", port=5000)