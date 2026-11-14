use actix_web::{get, post, web, App, HttpResponse, HttpServer, Responder, cookie::{Cookie, CookieName}};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::env;
use std::sync::{Arc, Mutex};

// --- Models ---

#[derive(Deserialize)]
struct RegisterRequest {
    email: String,
    name: String,
    password: String,
}

#[derive(Deserialize)]
struct LoginRequest {
    email: String,
    password: String,
}

#[derive(Deserialize)]
struct UploadWaresRequest {
    csv: String,
}

#[derive(Deserialize)]
struct WaresQuery {
    minPrice: Option<f64>,
    maxPrice: Option<f64>,
}

struct AppState {
    db: Mutex<Connection>,
    secret: String,
}

// --- Database Helpers ---

fn init_db() -> Connection {
    let conn = Connection::open("db.sqlite3").expect("Failed to open database");
    conn.execute(
        "CREATE TABLE IF NOT EXISTS merchants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password TEXT NOT NULL
        )",
        [],
    ).unwrap();
    conn.execute(
        "CREATE TABLE IF NOT EXISTS wares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            merchant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            FOREIGN KEY(merchant_id) REFERENCES merchants(id)
        )",
        [],
    ).unwrap();
    conn
}

// Simple session management using a cookie containing the merchant_id signed with APP_SECRET
// In a real app, we'd use a proper JWT or session store.
fn create_session_cookie(merchant_id: i64, secret: &str) -> Cookie {
    let value = format!("{}:{}", merchant_id, secret);
    Cookie::build("AUTH_COOKIE", value)
        .path("/")
        .http_only(true)
        .finish()
}

fn verify_session(cookie: &Cookie, secret: &str) -> Option<i64> {
    let val = cookie.value();
    let parts: Vec<&str> = val.split(':').collect();
    if parts.len() == 2 && parts[1] == secret {
        parts[0].parse::<i64>().ok()
    } else {
        None
    }
}

// --- Handlers ---

#[post("/merchants/register")]
async fn register(data: web::Data<AppState>, body: web::Json<RegisterRequest>) -> impl Responder {
    let conn = data.db.lock().unwrap();
    let res = conn.execute(
        "INSERT INTO merchants (email, name, password) VALUES (?1, ?2, ?3)",
        params![body.email, body.name, body.password],
    );

    match res {
        Ok(_) => HttpResponse::Created().finish(),
        Err(_) => HttpResponse::BadRequest().body("Invalid input or merchant already exists"),
    }
}

#[post("/merchants/login")]
async fn login(data: web::Data<AppState>, body: web::Json<LoginRequest>) -> impl Responder {
    let conn = data.db.lock().unwrap();
    let mut stmt = conn.prepare("SELECT id FROM merchants WHERE email = ?1 AND password = ?2").unwrap();
    let merchant_id: Option<i64> = stmt.query_row(params![body.email, body.password], |row| row.get(0)).ok();

    if let Some(id) = merchant_id {
        let cookie = create_session_cookie(id, &data.secret);
        HttpResponse::Ok()
            .cookie(cookie)
            .json("Login successful")
    } else {
        HttpResponse::Unauthorized().json(serde_json::json!({"error": "Invalid email or password"}))
    }
}

#[post("/merchants/upload-wares")]
async fn upload_wares(data: web::Data<AppState>, req: actix_web::HttpRequest, body: web::Json<UploadWaresRequest>) -> impl Responder {
    let cookie = req.cookie("AUTH_COOKIE");
    let merchant_id = if let Some(c) = cookie {
        verify_session(c, &data.secret)
    } else {
        None
    };

    let mid = match merchant_id {
        Some(id) => id,
        None => return HttpResponse::Unauthorized().finish(),
    };

    let conn = data.db.lock().unwrap();
    let lines = body.csv.split('\n');
    
    for line in lines {
        if line.trim().is_empty() { continue; }
        let cols: Vec<&str> = line.split(',').collect();
        if cols.len() != 3 {
            return HttpResponse::BadRequest().body("Invalid CSV format");
        }
        
        let name = cols[0].trim();
        let desc = cols[1].trim();
        let price = cols[2].trim().parse::<f64>().map_err(|_| HttpResponse::BadRequest().body("Invalid price"));
        
        if let Ok(p) = price {
            if let Err(_) = conn.execute(
                "INSERT INTO wares (merchant_id, name, description, price) VALUES (?1, ?2, ?3, ?4)",
                params![mid, name, desc, p],
            ) {
                return HttpResponse::InternalServerError().finish();
            }
        } else {
            return HttpResponse::BadRequest().body("Invalid price");
        }
    }

    HttpResponse::Ok().finish()
}

#[get("/wares")]
async fn get_wares(data: web::Data<AppState>, req: actix_web::HttpRequest, query: web::Query<WaresQuery>) -> impl Responder {
    let cookie = req.cookie("AUTH_COOKIE");
    let authenticated = if let Some(c) = cookie {
        verify_session(c, &data.secret).is_some()
    } else {
        false
    };

    if !authenticated {
        return HttpResponse::Unauthorized().finish();
    }

    let conn = data.db.lock().unwrap();
    let mut sql = "SELECT w.name, w.price, w.description, m.email 
                   FROM wares w JOIN merchants m ON w.merchant_id = m.id WHERE 1=1".to_string();
    
    let mut params_vec: Vec<Box<dyn rusqlite::ToSql>> = Vec::new();

    if let Some(min) = query.minPrice {
        sql.push_str(" AND w.price >= ?");
        params_vec.push(Box::new(min));
    }
    if let Some(max) = query.maxPrice {
        sql.push_str(" AND w.price <= ?");
        params_vec.push(Box::new(max));
    }

    let mut stmt = conn.prepare(&sql).unwrap();
    let rows = stmt.query_map(rusqlite::params_from_iter(params_vec), |row| {
        Ok((row.get::<_, String>(0)?, row.get::<_, f64>(1)?, row.get::<_, String>(2)?, row.get::<_, String>(3)?))
    }).unwrap();

    let mut html = String::from("<html><body><table border='1'><tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr>");
    for row in rows {
        if let Ok((name, price, desc, email)) = row {
            html.push_str(&format!("<tr><td>{}</td><td>{:.2}</td><td>{}</td><td>{}</td></tr>", name, price, desc, email));
        }
    }
    html.push_str("</table></body></html>");

    HttpResponse::Ok().content_type("text/html").body(html)
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let secret = env::var("APP_SECRET").unwrap_or_else(|_| "default_secret_key".to_string());
    let db_conn = init_db();
    
    let app_state = web::Data::new(AppState {
        db: Mutex::new(db_conn),
        secret,
    });

    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .service(register)
            .service(login)
            .service(upload_wares)
            .service(get_wares)
    })
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}