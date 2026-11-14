import os
import sqlite3
import csv
import io
import html as html_escaper
from typing import Optional
from fastapi import FastAPI, Request, Response, HTTPException, Depends, Cookie
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr, Field
from jose import jwt, JWTError
from passlib.context import CryptContext
from datetime import datetime, timedelta

# Configuration
APP_SECRET = os.getenv("APP_SECRET", "default_secret_key_for_dev")
DB_PATH = "db.sqlite3"
ALGORITHM = "HS256"
COOKIE_NAME = "AUTH_COOKIE"

# Resource limits
MAX_CSV_SIZE = 1_000_000  # 1MB limit to prevent resource exhaustion

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
    name: str = Field(..., max_length=255)
    password: str = Field(..., min_length=8, max_length=128)

class MerchantLogin(BaseModel):
    email: EmailStr
    password: str

class WareUpload(BaseModel):
    csv: str = Field(..., max_length=MAX_CSV_SIZE)

# Auth Helpers
def create_access_token(data: dict):
    # Use UTC for consistency
    expire = datetime.utcnow() + timedelta(days=1)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, APP_SECRET, algorithm=ALGORITHM)

def get_current_merchant(auth_cookie: Optional[str] = Cookie(None, alias=COOKIE_NAME)):
    if not auth_cookie:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        # Verify signature and algorithm explicitly
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
            # Parameterized query prevents SQL injection
            conn.execute("INSERT INTO merchants (email, name, password) VALUES (?, ?, ?)", 
                        (merchant.email, merchant.name, hashed_pw))
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Merchant already exists")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid input")
    return {"message": "Merchant registered successfully"}

@app.post("/merchants/login")
async def login(merchant: MerchantLogin, response: Response):
    try:
        with get_db() as conn:
            user = conn.execute("SELECT password FROM merchants WHERE email = ?", (merchant.email,)).fetchone()
            # passlib.verify uses constant-time comparison
            if user and pwd_context.verify(merchant.password, user["password"]):
                token = create_access_token({"sub": merchant.email})
                # Set httponly and secure flags to prevent XSS/MITM
                response.set_cookie(
                    key=COOKIE_NAME, 
                    value=token, 
                    httponly=True, 
                    samesite="Lax", 
                    secure=True if os.getenv("ENV") == "production" else False
                )
                return "Login successful"
    except Exception:
        # Generic error to avoid leaking internal details
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    raise HTTPException(status_code=401, detail="Invalid email or password")

@app.post("/merchants/upload-wares")
async def upload_wares(data: WareUpload, merchant_email: str = Depends(get_current_merchant)):
    # Use io.StringIO to process the string as a file for the csv module
    f = io.StringIO(data.csv)
    reader = csv.reader(f)
    try:
        rows = list(reader)
        if not rows:
            raise ValueError("Empty CSV")
        
        # Limit number of rows to prevent resource exhaustion
        if len(rows) > 1000:
            raise ValueError("CSV too large: maximum 1000 rows allowed")

        with get_db() as conn:
            for row in rows:
                if len(row) != 3:
                    raise ValueError("Invalid CSV format: each row must have name, description, price")
                
                name, desc, price_str = row
                # Explicit float conversion validates numeric input
                price = float(price_str)
                
                # Parameterized query prevents SQL injection
                conn.execute("INSERT INTO wares (merchant_email, name, description, price) VALUES (?, ?, ?, ?)",
                            (merchant_email, name, desc, price))
            conn.commit()
    except (ValueError, IndexError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid CSV format")
    
    return {"message": "Wares uploaded successfully"}

@app.get("/wares", response_class=HTMLResponse)
async def get_wares(
    request: Request, 
    minPrice: Optional[float] = None, 
    maxPrice: Optional[float] = None, 
    auth_cookie: Optional[str] = Cookie(None, alias=COOKIE_NAME)
):
    if not auth_cookie:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Verify token even for the GET request as per security schema
    try:
        jwt.decode(auth_cookie, APP_SECRET, algorithms=[ALGORITHM])
    except JWTError:
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

    try:
        with get_db() as conn:
            rows = conn.execute(query, params).fetchall()
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

    # Render HTML Table with strict escaping to prevent XSS
    html = "<table border='1'><thead><tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr></thead><tbody>"
    for row in rows:
        # Escape all user-generated content before inserting into HTML
        safe_name = html_escaper.escape(str(row['name']))
        safe_price = html_escaper.escape(str(row['price']))
        safe_desc = html_escaper.escape(str(row['description']))
        safe_email = html_escaper.escape(str(row['merchant_email']))
        
        html += f"<tr><td>{safe_name}</td><td>{safe_price}</td><td>{safe_desc}</td><td>{safe_email}</td></tr>"
    html += "</tbody></table>"
    
    return html

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)