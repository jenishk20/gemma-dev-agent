use actix_web::{get, post, web, App, HttpResponse, HttpServer, Responder, Cookie, HttpRequest, HttpResponseBuilder};
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
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password TEXT NOT NULL
        )",
        [],
    ).unwrap();
    conn.execute(
        "CREATE TABLE IF NOT EXISTS wares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            merchant_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY(merchant_id) REFERENCES merchants(id)
        )",
        [],
    ).unwrap();
    conn
}

// --- Auth Helper ---

fn get_auth_user(req: HttpRequest, state: &AppState) -> Option<String> {
    let cookie = req.cookie("AUTH_COOKIE")?;
    let token = cookie.value();
    // Simple token format: "merchant_id:signature"
    let parts: Vec<&str> = token.split(':').collect();
    if parts.len() != 2 { return None; }
    
    let merchant_id = parts[0];
    let signature = parts[1];
    
    // Verify signature using APP_SECRET
    let expected_sig = format!("{:x}", md5_simple(merchant_id, &state.secret));
    if signature == expected_sig {
        Some(merchant_id.to_string())
    } else {
        None
    }
}

fn md5_simple(data: &str, secret: &str) -> String {
    // Since we can't use external crypto crates not listed, we use a basic hash
    // for the purpose of this exercise to simulate a signed cookie.
    let combined = format!("{}:{}", data, secret);
    let mut hash: u64 = 0;
    for c in combined.bytes() {
        hash = hash.wrapping_add(c as u64).wrapping_mul(31);
    }
    format!("{:x}", hash)
}

// --- Handlers ---

#[post("/merchants/register")]
async fn register(state: web::Data<AppState>, body: web::Json<RegisterRequest>) -> impl Responder {
    let db = state.db.lock().unwrap();
    let id = uuid::Uuid::new_v4().to_string();
    
    let res = db.execute(
        "INSERT INTO merchants (id, email, name, password) VALUES (?1, ?2, ?3, ?4)",
        params![id, body.email, body.name, body.password],
    );

    match res {
        Ok(_) => HttpResponse::Created().finish(),
        Err(_) => HttpResponse::BadRequest().body("Invalid input or email already exists"),
    }
}

#[post("/merchants/login")]
async fn login(state: web::Data<AppState>, body: web::Json<LoginRequest>) -> impl Responder {
    let db = state.db.lock().unwrap();
    let mut stmt = db.prepare("SELECT id FROM merchants WHERE email = ?1 AND password = ?2").unwrap();
    let merchant_id: Option<String> = stmt.query_row(params![body.email, body.password], |row| row.get(0)).ok();

    if let Some(id) = merchant_id {
        let sig = md5_simple(&id, &state.secret);
        let cookie_val = format!("{}:{}", id, sig);
        let cookie = Cookie::build("AUTH_COOKIE", cookie_val).path("/").finish();
        HttpResponse::Ok().cookie(cookie).body("Login successful")
    } else {
        HttpResponse::Unauthorized().json(serde_json::json!({"error": "Invalid email or password"}))
    }
}

#[post("/merchants/upload-wares")]
async fn upload_wares(req: HttpRequest, state: web::Data<AppState>, body: web::Json<UploadWaresRequest>) -> impl Responder {
    let user_id = match get_auth_user(req, &state) {
        Some(id) => id,
        None => return HttpResponse::Unauthorized().finish(),
    };

    let db = state.db.lock().unwrap();
    let lines = body.csv.split('\n');

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
            Err(_) => return HttpResponse::BadRequest().body("Invalid price format"),
        };

        if let Err(_) = db.execute(
            "INSERT INTO wares (merchant_id, name, description, price) VALUES (?1, ?2, ?3, ?4)",
            params![user_id, name, desc, price],
        ) {
            return HttpResponse::InternalServerError().finish();
        }
    }

    HttpResponse::Ok().body("Wares uploaded successfully")
}

#[get("/wares")]
async fn get_wares(req: HttpRequest, state: web::Data<AppState>, query: web::Query<WaresQuery>) -> impl Responder {
    // The schema says security: cookieAuth, but usually a public catalog is open. 
    // However, following the schema strictly:
    if get_auth_user(req, &state).is_none() {
        return HttpResponse::Unauthorized().finish();
    }

    let db = state.db.lock().unwrap();
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
    .bind("0.0.0.0:5000")?
    .run()
    .await
}