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

#[derive(Serialize)]
struct LoginResponse {
    token: String,
    message: String,
}

#[derive(Deserialize)]
struct RegisterRequest {
    email: String,
    password: String,
    name: String,
}

#[derive(Serialize)]
struct MessageResponse {
    message: String,
}

// --- Database Logic ---

struct DbState {
    conn: Mutex<Connection>,
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
async fn register(data: web::Data<Arc<DbState>>, body: web::Json<RegisterRequest>) -> impl Responder {
    let conn = data.conn.lock().unwrap();
    
    let result = conn.execute(
        "INSERT INTO users (email, password, name) VALUES (?1, ?2, ?3)",
        params![body.email, body.password, body.name],
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
async fn login(data: web::Data<Arc<DbState>>, body: web::Json<LoginRequest>) -> impl Responder {
    let conn = data.conn.lock().unwrap();
    let secret = env::var("APP_SECRET").unwrap_or_else(|_| "default_secret".to_string());

    let mut stmt = conn
        .prepare("SELECT id FROM users WHERE email = ?1 AND password = ?2")
        .expect("Query preparation failed");
    
    let user_exists = stmt.query_row(params![body.email, body.password], |_| Ok(())).is_ok();

    if user_exists {
        // In a real app, we would generate a real JWT. 
        // Here we simulate a token using the secret and the email.
        let token = format!("jwt-token-{}-{}", secret, uuid::Uuid::new_v4());
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

    let db_conn = init_db();
    let state = Arc::new(DbState {
        conn: Mutex::new(db_conn),
    });

    println!("Server starting on 0.0.0.0:5000");
    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(state.clone()))
            .service(register)
            .service(login)
    })
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}