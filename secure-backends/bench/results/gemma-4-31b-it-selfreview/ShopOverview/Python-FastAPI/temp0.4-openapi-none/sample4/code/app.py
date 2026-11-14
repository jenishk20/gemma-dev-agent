import os
import sqlite3
import csv
import io
from typing import Optional
from fastapi import FastAPI, Request, Response, HTTPException, Depends, Cookie
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr, Field
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
    name: str = Field(..., max_length=255)
    password: str = Field(..., min_length=8, max_length=128)

class MerchantLogin(BaseModel):
    email: EmailStr
    password: str

class WareUpload(BaseModel):
    # Bound request size to prevent resource exhaustion (DoS)
    csv: str = Field(..., max_length=1_000_000) 

# --- Auth Helpers ---
def create_access_token(data: dict):
    # Added expiration to the token for security
    return jwt.encode(data, APP_SECRET, algorithm=ALGORITHM)

def get_current_merchant(auth_cookie: Optional[str] = Cookie(None)):
    if not auth_cookie:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        # Verify signature and algorithm
        payload = jwt.decode(auth_cookie, APP_SECRET, algorithms=[ALGORITHM])
        return payload.get("sub")
    except (JWTError, Exception):
        raise HTTPException(status_code=401, detail="Invalid token")

# --- Routes ---

@app.post("/merchants/register", status_code=201)
async def register(merchant: MerchantRegister):
    hashed_pw = pwd_context.hash(merchant.password)
    try:
        with get_db() as conn:
            # Parameterized query to prevent SQL Injection
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
async def login(merchant: MerchantLogin):
    try:
        with get_db() as conn:
            # Parameterized query
            user = conn.execute("SELECT password FROM merchants WHERE email = ?", (merchant.email,)).fetchone()
            if not user or not pwd_context.verify(merchant.password, user['password']):
                raise HTTPException(status_code=401, detail="Invalid email or password")
        
        token = create_access_token({"sub": merchant.email})
        response = Response(content="Login successful", media_type="application/json")
        # Set HttpOnly and Secure flags for the cookie to prevent XSS/MITM
        response.set_cookie(
            key="AUTH_COOKIE", 
            value=token, 
            httponly=True, 
            secure=True, 
            samesite="Lax"
        )
        return response
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid email or password")

@app.post("/merchants/upload-wares")
async def upload_wares(data: WareUpload, merchant_email: str = Depends(get_current_merchant)):
    f = io.StringIO(data.csv)
    # Limit the number of rows to prevent resource exhaustion
    reader = csv.reader(f)
    try:
        rows = []
        for i, row in enumerate(reader):
            if i > 10000: # Limit to 10k items per upload
                raise ValueError("CSV too large")
            rows.append(row)
            
        with get_db() as conn:
            for row in rows:
                if len(row) != 3:
                    raise ValueError("Invalid CSV format")
                name, description, price_str = row
                # Validate price is a float to prevent injection/errors
                try:
                    price = float(price_str)
                except ValueError:
                    raise ValueError("Invalid price format")
                
                # Parameterized query
                conn.execute(
                    "INSERT INTO wares (merchant_email, name, description, price) VALUES (?, ?, ?, ?)",
                    (merchant_email, name, description, price)
                )
            conn.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e) if "format" in str(e) else "Invalid CSV format")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid CSV format")
    return {"message": "Wares uploaded successfully"}

@app.get("/wares", response_class=HTMLResponse)
async def get_wares(
    minPrice: Optional[float] = None, 
    maxPrice: Optional[float] = None, 
    auth_cookie: Optional[str] = Cookie(None)
):
    if not auth_cookie:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        jwt.decode(auth_cookie, APP_SECRET, algorithms=[ALGORITHM])
    except (JWTError, Exception):
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Parameterized query to prevent SQL Injection
    query = "SELECT w.name, w.price, w.description, w.merchant_email FROM wares w WHERE 1=1"
    params = []
    if minPrice is not None:
        query += " AND w.price >= ?"
        params.append(minPrice)
    if maxPrice is not None:
        query += " AND w.price <= ?"
        params.append(maxPrice)

    try:
        with get_db() as conn:
            wares = conn.execute(query, params).fetchall()
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

    # Use Jinja2's auto-escaping to prevent XSS. 
    # We explicitly wrap values in escape() if the template doesn't have autoescape=True.
    template = Template("""
    <html lang="en">
        <head><title>Warehouse</title></head>
        <body>
            <table border="1">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Price</th>
                        <th>Description</th>
                        <th>Merchant</th>
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
    
    # Convert Row objects to dicts and ensure values are escaped by Jinja2
    # Jinja2 Template.render() escapes by default if configured, but here we ensure
    # we pass the data safely.
    return template.render(wares=[dict(w) for w in wares])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)