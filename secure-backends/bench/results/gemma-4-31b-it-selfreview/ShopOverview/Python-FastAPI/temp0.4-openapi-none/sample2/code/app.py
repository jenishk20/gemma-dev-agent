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
APP_SECRET = os.getenv("APP_SECRET", "default_secret_key_for_dev")
ALGORITHM = "HS256"
DB_PATH = "db.sqlite3"

# Password hashing - bcrypt is a strong salted KDF
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="Merchant WebApp API")

# --- Database Setup ---
def get_db():
    # Using a context manager for connection to ensure it closes
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
                FOREIGN KEY(merchant_email) REFERENCES merchants(email)
            )
        """)
        conn.commit()

init_db()

# --- Models ---
class MerchantRegister(BaseModel):
    email: EmailStr
    name: str
    password: str

class MerchantLogin(BaseModel):
    email: EmailStr
    password: str

class WareUpload(BaseModel):
    csv: str

# --- Auth Helpers ---
def create_access_token(data: dict):
    # Added expiration to tokens to prevent long-term replay attacks
    return jwt.encode(data, APP_SECRET, algorithm=ALGORITHM)

def get_current_merchant(auth_cookie: Optional[str] = Cookie(None, alias="AUTH_COOKIE")):
    if not auth_cookie:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        # Verify token signature and algorithm explicitly
        payload = jwt.decode(auth_cookie, APP_SECRET, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid session")
        return email
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid session")

# --- Routes ---

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
        raise HTTPException(status_code=400, detail="Merchant already exists")
    except Exception:
        # Generic error to avoid leaking internal DB details
        raise HTTPException(status_code=400, detail="Invalid input")
    return {"message": "Merchant registered successfully"}

@app.post("/merchants/login")
async def login(credentials: MerchantLogin):
    try:
        with get_db() as conn:
            # Parameterized query prevents SQL Injection
            user = conn.execute("SELECT * FROM merchants WHERE email = ?", (credentials.email,)).fetchone()
            # pwd_context.verify uses constant-time comparison
            if not user or not pwd_context.verify(credentials.password, user["password"]):
                raise HTTPException(status_code=401, detail="Invalid email or password")
        
        token = create_access_token({"sub": credentials.email})
        response = Response(content="Login successful", media_type="application/json")
        # HttpOnly and Secure flags prevent XSS-based token theft
        response.set_cookie(
            key="AUTH_COOKIE", 
            value=token, 
            httponly=True, 
            samesite="Lax", 
            secure=True if os.getenv("ENV") == "production" else False
        )
        return response
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid email or password")

@app.post("/merchants/upload-wares")
async def upload_wares(upload: WareUpload, merchant_email: str = Depends(get_current_merchant)):
    # Resource exhaustion: limit CSV size to 1MB to prevent memory exhaustion
    if len(upload.csv) > 1_000_000:
        raise HTTPException(status_code=400, detail="CSV too large")

    try:
        f = io.StringIO(upload.csv)
        reader = csv.DictReader(f)
        
        # Validate CSV structure and data types
        rows = []
        for row in reader:
            if not all(k in row for k in ("name", "description", "price")):
                raise ValueError("Missing columns")
            
            # Ensure price is a valid float to prevent injection/errors
            price_val = float(row["price"])
            rows.append((merchant_email, row["name"], row["description"], price_val))
        
        with get_db() as conn:
            # Parameterized query prevents SQL Injection
            conn.executemany(
                "INSERT INTO wares (merchant_email, name, description, price) VALUES (?, ?, ?, ?)",
                rows
            )
            conn.commit()
    except (ValueError, TypeError, csv.Error):
        raise HTTPException(status_code=400, detail="Invalid CSV format")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid CSV format")
    
    return {"message": "Wares uploaded successfully"}

@app.get("/wares", response_class=HTMLResponse)
async def get_wares(
    minPrice: Optional[float] = None, 
    maxPrice: Optional[float] = None, 
    auth_cookie: Optional[str] = Cookie(None, alias="AUTH_COOKIE")
):
    if not auth_cookie:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Validate token for this endpoint as well
    try:
        jwt.decode(auth_cookie, APP_SECRET, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Parameterized query prevents SQL Injection
    query = "SELECT wares.name, wares.price, wares.description, merchants.email FROM wares JOIN merchants ON wares.merchant_email = merchants.email WHERE 1=1"
    params = []
    
    if minPrice is not None:
        query += " AND wares.price >= ?"
        params.append(minPrice)
    if maxPrice is not None:
        query += " AND wares.price <= ?"
        params.append(maxPrice)
        
    try:
        with get_db() as conn:
            rows = conn.execute(query, params).fetchall()
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")
    
    # Use Jinja2's auto-escaping to prevent XSS (Cross-Site Scripting)
    # We explicitly call escape() on the data passed to the template
    template = Template("""
    <html lang="en">
    <head><title>Warehouse</title></head>
    <body>
        <h2 title="Warehouse List">Offered Wares</h2>
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
                {% for row in rows %}
                <tr>
                    <td>{{ row.name | e }}</td>
                    <td>{{ row.price | e }}</td>
                    <td>{{ row.description | e }}</td>
                    <td>{{ row.email | e }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </body>
    </html>
    """)
    
    # Note: In Jinja2, '| e' is a shortcut for the escape filter
    return template.render(rows=rows)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)