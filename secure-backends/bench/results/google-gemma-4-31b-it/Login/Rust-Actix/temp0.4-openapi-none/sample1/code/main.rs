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

// --- Handlers ---

#[post("/register")]
async fn register(data: web::Data<AppState>, req: web::Json<RegisterRequest>) -> impl Responder {
    let db = data.db.lock().unwrap();
    
    // Check if user exists
    let mut stmt = db.prepare("SELECT id FROM users WHERE email = ?").unwrap();
    let exists = stmt.exists(params![req.email]).unwrap();

    if exists {
        return HttpResponse::BadRequest().json(MessageResponse {
            message: "Email already in use or invalid data".to_string(),
        });
    }

    // Insert user
    let res = db.execute(
        "INSERT INTO users (email, password, name) VALUES (?, ?, ?)",
        params![req.email, req.password, req.name],
    );

    match res {
        Ok(_) => HttpResponse::Created().json(MessageResponse {
            message: "Registration successful".to_string(),
        }),
        Err(_) => HttpResponse::InternalServerError().json(MessageResponse {
            message: "Database error".to_string(),
        }),
    }
}

#[post("/login")]
async fn login(data: web::Data<AppState>, req: web::Json<LoginRequest>) -> impl Responder {
    let db = data.db.lock().unwrap();
    
    let mut stmt = db.prepare("SELECT id FROM users WHERE email = ? AND password = ?").unwrap();
    let user_id: Result<i32, rusqlite::Error> = stmt.query_row(params![req.email, req.password], |row| row.get(0));

    match user_id {
        Ok(id) => {
            // In a real app, we would sign a JWT here using data.secret
            // For this implementation, we generate a pseudo-token combining secret and user id
            let token = format!("{}-{}-{}", data.secret, id, uuid::Uuid::new_v4());
            HttpResponse::Ok().json(LoginResponse {
                token,
                message: "Login successful".to_string(),
            })
        }
        Err(_) => HttpResponse::Unauthorized().json(MessageResponse {
            message: "Invalid email or password".to_string(),
        }),
    }
}

// --- Main ---

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();

    // Database initialization
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

    // Get secret from env
    let secret = env::var("APP_SECRET").unwrap_or_else(|_| "default_secret_key".to_string());

    let app_state = web::Data::new(AppState {
        db: Mutex::new(conn),
        secret,
    });

    println!("Server starting on 0.0.0.0:5000...");
    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .service(register)
            .service(login)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}