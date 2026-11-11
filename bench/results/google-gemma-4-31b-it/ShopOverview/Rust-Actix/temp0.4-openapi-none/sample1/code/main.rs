use actix_web::{get, post, web, App, HttpResponse, HttpServer, Responder, cookie::{Cookie, SameSite}};
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
    min_price: Option<f64>,
    max_price: Option<f64>,
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
    ).expect("Failed to create merchants table");

    conn.execute(
        "CREATE TABLE IF NOT EXISTS wares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            merchant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY(merchant_id) REFERENCES merchants(id)
        )",
        [],
    ).expect("Failed to create wares table");
    conn
}

// Simple session management: Cookie value is "email|secret_hash"
// In a real app, we'd use a proper session store or JWT.
fn create_session_cookie(email: &str, secret: &str) -> Cookie<'static> {
    let session_val = format!("{}:{}", email, secret); 
    Cookie::build("AUTH_COOKIE", session_val)
        .path("/")
        .http_only(true)
        .same_site(SameSite::Strict)
        .finish()
}

fn verify_session(req: actix_web::HttpRequest, secret: &str) -> Option<String> {
    let cookie = req.cookie("AUTH_COOKIE")?;
    let parts: Vec<&str> = cookie.value().split(':').collect();
    if parts.len() == 2 && parts[1] == secret {
        Some(parts[0].to_string())
    } else {
        None
    }
}

// --- Handlers ---

#[post("/merchants/register")]
async fn register(data: web::Data<AppState>, req: web::Json<RegisterRequest>) -> impl Responder {
    let mut db = data.db.lock().unwrap();
    let res = db.execute(
        "INSERT INTO merchants (email, name, password) VALUES (?1, ?2, ?3)",
        params![req.email, req.name, req.password],
    );

    match res {
        Ok(_) => HttpResponse::Created().finish(),
        Err(_) => HttpResponse::BadRequest().body("Invalid input or email already exists"),
    }
}

#[post("/merchants/login")]
async fn login(data: web::Data<AppState>, req: web::Json<LoginRequest>) -> impl Responder {
    let db = data.db.lock().unwrap();
    let mut stmt = db.prepare("SELECT id FROM merchants WHERE email = ?1 AND password = ?2").unwrap();
    let merchant_id: Option<i32> = stmt.query_row(params![req.email, req.password], |row| row.get(0)).ok();

    if let Some(_) = merchant_id {
        let cookie = create_session_cookie(&req.email, &data.secret);
        HttpResponse::Ok()
            .cookie(cookie)
            .json("Login successful")
    } else {
        HttpResponse::Unauthorized().json(serde_json::json!({"error": "Invalid email or password"}))
    }
}

#[post("/merchants/upload-wares")]
async fn upload_wares(data: web::Data<AppState>, req: actix_web::HttpRequest, body: web::Json<UploadWaresRequest>) -> impl Responder {
    let email = match verify_session(req, &data.secret) {
        Some(e) => e,
        None => return HttpResponse::Unauthorized().finish(),
    };

    let mut db = data.db.lock().unwrap();
    
    // Get merchant id
    let merchant_id: i32 = match db.query_row("SELECT id FROM merchants WHERE email = ?1", params![email], |row| row.get(0)) {
        Ok(id) => id,
        Err(_) => return HttpResponse::Unauthorized().finish(),
    };

    let lines = body.csv.lines();
    for line in lines {
        if line.trim().is_empty() { continue; }
        let cols: Vec<&str> = line.split(',').collect();
        if cols.len() != 3 {
            return HttpResponse::BadRequest().body("Invalid CSV format");
        }
        let name = cols[0].trim();
        let desc = cols[1].trim();
        let price: f64 = match cols[2].trim().parse() {
            Ok(p) => p,
            Err(_) => return HttpResponse::BadRequest().body("Invalid price in CSV"),
        };

        if let Err(_) = db.execute(
            "INSERT INTO wares (merchant_id, name, description, price) VALUES (?1, ?2, ?3, ?4)",
            params![merchant_id, name, desc, price],
        ) {
            return HttpResponse::InternalServerError().finish();
        }
    }

    HttpResponse::Ok().finish()
}

#[get("/wares")]
async fn get_wares(data: web::Data<AppState>, req: actix_web::HttpRequest, query: web::Query<WaresQuery>) -> impl Responder {
    // The schema says security: cookieAuth, but usually a public catalog is open. 
    // However, following the schema strictly:
    if verify_session(req, &data.secret).is_none() {
        return HttpResponse::Unauthorized().finish();
    }

    let db = data.db.lock().unwrap();
    let mut sql = "SELECT w.name, w.price, w.description, m.email 
                   FROM wares w JOIN merchants m ON w.merchant_id = m.id WHERE 1=1".to_string();
    
    let mut params_vec: Vec<f64> = Vec::new();
    if let Some(min) = query.min_price {
        sql.push_str(" AND w.price >= ?");
        params_vec.push(min);
    }
    if let Some(max) = query.max_price {
        sql.push_str(" AND w.price <= ?");
        params_vec.push(max);
    }

    let mut stmt = db.prepare(&sql).unwrap();
    let rows = stmt.query_map(rusqlite::params_from_iter(params_vec), |row| {
        Ok((
            row.get::<_, String>(0)?,
            row.get::<_, f64>(1)?,
            row.get::<_, String>(2)?,
            row.get::<_, String>(3)?,
        ))
    }).unwrap();

    let mut html = String::from("<html><body><table border='1'><tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr>");
    for row in rows {
        if let Ok((name, price, desc, email)) = row {
            html.push_str(&format!("<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>", name, price, desc, email));
        }
    }
    html.push_str("</table></body></html>");

    HttpResponse::Ok().content_type("text/html").body(html)
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();
    
    let secret = env::var("APP_SECRET").unwrap_or_else(|_| "default_secret_key".to_string());
    let db_conn = init_db();
    
    let state = web::Data::new(AppState {
        db: Mutex::new(db_conn),
        secret,
    });

    HttpServer::new(move || {
        App::new()
            .app_data(state.clone())
            .service(register)
            .service(login)
            .service(upload_wares)
            .service(get_wares)
    })
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}