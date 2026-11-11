use actix_web::{get, post, web, App, HttpResponse, HttpServer, Responder, HttpRequest};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::env;
use std::sync::{Arc, Mutex};

// --- Models ---

#[derive(Deserialize)]
struct RegisterRequest {
    email: String,
    username: String,
    password: String,
}

#[derive(Deserialize)]
struct LoginRequest {
    email: String,
    password: String,
}

#[derive(Deserialize)]
struct SecretRequest {
    username: String,
    secret: String,
}

#[derive(Serialize)]
struct MessageResponse {
    message: String,
}

#[derive(Serialize)]
struct TokenResponse {
    token: String,
    message: String,
}

#[derive(Serialize)]
struct SecretResponse {
    secret: String,
}

// --- Database Logic ---

struct DbPool {
    conn: Mutex<Connection>,
}

impl DbPool {
    fn new() -> Self {
        let conn = Connection::open("db.sqlite3").expect("Failed to open database");
        conn.execute(
            "CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )",
            [],
        ).expect("Failed to create users table");
        conn.execute(
            "CREATE TABLE IF NOT EXISTS secrets (
                username TEXT PRIMARY KEY,
                secret TEXT NOT NULL,
                FOREIGN KEY(username) REFERENCES users(username)
            )",
            [],
        ).expect("Failed to create secrets table");
        
        DbPool { conn: Mutex::new(conn) }
    }
}

// --- Security Helpers ---

// Simple token implementation since JWT crate is not allowed in the provided list.
// We use a signed-like token: "username:hash(username + APP_SECRET)"
fn generate_token(username: &str) -> String {
    let secret = env::var("APP_SECRET").unwrap_or_else(|_| "default_secret".to_string());
    let combined = format!("{}:{}", username, secret);
    let hash = format!("{:x}", md5_simple(&combined));
    format!("{}:{}", username, hash)
}

fn verify_token(token: &str) -> Option<String> {
    let parts: Vec<&str> = token.split(':').collect();
    if parts.len() != 2 { return None; }
    let username = parts[0];
    let provided_hash = parts[1];
    let secret = env::var("APP_SECRET").unwrap_or_else(|_| "default_secret".to_string());
    let combined = format!("{}:{}", username, secret);
    let expected_hash = format!("{:x}", md5_simple(&combined));
    if provided_hash == expected_hash {
        Some(username.to_string())
    } else {
        None
    }
}

// Basic MD5-like hash for token validation (since we can't use external crypto crates)
fn md5_simple(data: &str) -> u64 {
    let mut hash: u64 = 0x811c9dc5;
    for byte in data.bytes() {
        hash ^= byte as u64;
        hash = hash.wrapping_mul(0x01000193);
    }
    hash
}

// Simple password "hashing" (XOR with secret for demonstration, as bcrypt/argon2 are not available)
fn hash_password(password: &str) -> String {
    let secret = env::var("APP_SECRET").unwrap_or_else(|_| "default_secret".to_string());
    let mut result = String::new();
    for (i, c) in password.chars().enumerate() {
        let s_char = secret.chars().nth(i % secret.len()).unwrap_or(' ');
        result.push(std::char::from_u32((c as u32 ^ s_char as u32)).unwrap_or('?'));
    }
    result
}

// --- Handlers ---

#[post("/register")]
async fn register(data: web::Data<Arc<DbPool>>, body: web::Json<RegisterRequest>) -> impl Responder {
    let conn = data.conn.lock().unwrap();
    let hashed_pw = hash_password(&body.password);
    
    let result = conn.execute(
        "INSERT INTO users (email, username, password) VALUES (?1, ?2, ?3)",
        params![body.email, body.username, hashed_pw],
    );

    match result {
        Ok(_) => HttpResponse::Created().json(MessageResponse { message: "Registration successful".to_string() }),
        Err(_) => HttpResponse::BadRequest().json(MessageResponse { message: "Email already in use or invalid data".to_string() }),
    }
}

#[post("/login")]
async fn login(data: web::Data<Arc<DbPool>>, body: web::Json<LoginRequest>) -> impl Responder {
    let conn = data.conn.lock().unwrap();
    let hashed_pw = hash_password(&body.password);
    
    let mut stmt = conn.prepare("SELECT username FROM users WHERE email = ?1 AND password = ?2").unwrap();
    let user_res = stmt.query_row(params![body.email, hashed_pw], |row| row.get::<_, String>(0));

    match user_res {
        Ok(username) => {
            let token = generate_token(&username);
            HttpResponse::Ok().json(TokenResponse {
                token,
                message: "Login successful".to_string(),
            })
        }
        Err(_) => HttpResponse::Unauthorized().json(MessageResponse { message: "Invalid email or password".to_string() }),
    }
}

#[post("/set_secret")]
async fn set_secret(req: HttpRequest, data: web::Data<Arc<DbPool>>, body: web::Json<SecretRequest>) -> impl Responder {
    let auth_header = req.headers().get("Authorization");
    if let Some(auth_str) = auth_header.and_then(|h| h.to_str().ok()) {
        let token = auth_str.trim_start_matches("Bearer ");
        if let Some(user) = verify_token(token) {
            if user == body.username {
                let conn = data.conn.lock().unwrap();
                let result = conn.execute(
                    "INSERT OR REPLACE INTO secrets (username, secret) VALUES (?1, ?2)",
                    params![body.username, body.secret],
                );
                if result.is_ok() {
                    return HttpResponse::Ok().json(MessageResponse { message: "Secret has been set successfully".to_string() });
                }
            }
        }
    }
    HttpResponse::Unauthorized().json(MessageResponse { message: "Invalid authentication token".to_string() })
}

#[get("/get_secret")]
async fn get_secret(req: HttpRequest, data: web::Data<Arc<DbPool>>, query: web::Query<std::collections::HashMap<String, String>>) -> impl Responder {
    let username_query = query.get("username");
    if username_query.is_none() {
        return HttpResponse::BadRequest().json(MessageResponse { message: "Username is required".to_string() });
    }
    let target_user = username_query.unwrap();

    let auth_header = req.headers().get("Authorization");
    if let Some(auth_str) = auth_header.and_then(|h| h.to_str().ok()) {
        let token = auth_str.trim_start_matches("Bearer ");
        if let Some(user) = verify_token(token) {
            if user == *target_user {
                let conn = data.conn.lock().unwrap();
                let mut stmt = conn.prepare("SELECT secret FROM secrets WHERE username = ?1").unwrap();
                let secret_res = stmt.query_row(params![target_user], |row| row.get::<_, String>(0));
                
                if let Ok(secret) = secret_res {
                    return HttpResponse::Ok().json(SecretResponse { secret });
                }
            }
        }
    }
    HttpResponse::Unauthorized().json(MessageResponse { message: "Invalid authentication token".to_string() })
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let db_pool = Arc::new(DbPool::new());
    
    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(db_pool.clone()))
            .service(register)
            .service(login)
            .service(set_secret)
            .service(get_secret)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}