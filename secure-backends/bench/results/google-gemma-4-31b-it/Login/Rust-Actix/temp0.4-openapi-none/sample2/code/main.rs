use actix_web::{post, web, App, HttpResponse, HttpServer, Responder};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::env;
use std::sync::{Arc, Mutex};

// --- Models ---

#[derive(Deserialize)]
struct LoginRequest {
    email: String,
    password: String,
}

#[derive(Deserialize)]
struct RegisterRequest {
    email: String,
    password: String,
    name: String,
}

#[derive(Serialize)]
struct LoginResponse {
    token: String,
    message: String,
}

#[derive(Serialize)]
struct MessageResponse {
    message: String,
}

// --- Database State ---

struct AppState {
    db: Mutex<Connection>,
    secret: String,
}

fn init_db() -> Connection {
    let conn = Connection::open("db.sqlite3").expect("Failed to open database");
    conn.execute(
        "CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            name TEXT NOT NULL
        )",
        [],
    ).expect("Failed to create table");
    conn
}

// --- Handlers ---

#[post("/register")]
async fn register(data: web::Data<AppState>, req: web::Json<RegisterRequest>) -> impl Responder {
    let db = data.db.lock().unwrap();
    
    let result = db.execute(
        "INSERT INTO users (email, password, name) VALUES (?1, ?2, ?3)",
        params![req.email, req.password, req.name],
    );

    match result {
        Ok(_) => HttpResponse::Created().json(MessageResponse {
            message: "Registration successful".to_string(),
        }),
        Err(_) => HttpResponse::BadRequest().json(MessageResponse {
            message: "Email already in use or invalid data".to_string(),
        }),
    }
}

#[post("/login")]
async fn login(data: web::Data<AppState>, req: web::Json<LoginRequest>) -> impl Responder {
    let db = data.db.lock().unwrap();
    
    let mut stmt = db
        .prepare("SELECT id FROM users WHERE email = ?1 AND password = ?2")
        .unwrap();
    
    let user_exists = stmt.query_row(params![req.email, req.password], |_| Ok(())).is_ok();

    if user_exists {
        // In a real app, we would use the secret to sign a JWT. 
        // Here we simulate a token using the secret and a UUID-like string.
        let token = format!("{}-{}", data.secret, uuid::Uuid::new_v4());
        HttpResponse::Ok().json(LoginResponse {
            token,
            message: "Login successful".to_string(),
        })
    } else {
        HttpResponse::Unauthorized().json(MessageResponse {
            message: "Invalid email or password".to_string(),
        })
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();

    let secret = env::var("APP_SECRET").unwrap_or_else(|_| "default_secret_key".to_string());
    let db_conn = init_db();

    let app_state = web::Data::new(AppState {
        db: Mutex::new(db_conn),
        secret,
    });

    println!("Starting server at http://0.0.0.0:5000");

    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .service(register)
            .service(login)
    })
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}