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

struct DbState {
    conn: Mutex<Connection>,
}

fn init_db() -> Connection {
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
            secret_value TEXT NOT NULL,
            FOREIGN KEY(username) REFERENCES users(username)
        )",
        [],
    ).expect("Failed to create secrets table");
    conn
}

// --- Security Helpers ---

// Simple token generation using APP_SECRET and username
// In a real app, use JWT. Given constraints and library list, we implement a signed-like token.
fn generate_token(username: &str) -> String {
    let secret = env::var("APP_SECRET").unwrap_or_else(|_| "default_secret".to_string());
    format!("{}:{}:{}", username, secret, uuid::Uuid::new_v4())
}

fn verify_token(token: &str, expected_username: &str) -> bool {
    let secret = env::var("APP_SECRET").unwrap_or_else(|_| "default_secret".to_string());
    // Token format: username:secret:uuid
    let parts: Vec<&str> = token.split(':').collect();
    if parts.len() != 3 {
        return false;
    }
    parts[0] == expected_username && parts[1] == secret
}

// --- Handlers ---

#[post("/register")]
async fn register(data: web::Data<Arc<DbState>>, req: web::Json<RegisterRequest>) -> impl Responder {
    let mut conn = data.conn.lock().unwrap();
    let res = conn.execute(
        "INSERT INTO users (email, username, password) VALUES (?1, ?2, ?3)",
        params![req.email, req.username, req.password],
    );

    match res {
        Ok(_) => HttpResponse::Created().json(MessageResponse {
            message: "Registration successful".to_string(),
        }),
        Err(_) => HttpResponse::BadRequest().json(MessageResponse {
            message: "Email already in use or invalid data".to_string(),
        }),
    }
}

#[post("/login")]
async fn login(data: web::Data<Arc<DbState>>, req: web::Json<LoginRequest>) -> impl Responder {
    let conn = data.conn.lock().unwrap();
    let mut stmt = conn
        .prepare("SELECT username FROM users WHERE email = ?1 AND password = ?2")
        .unwrap();
    
    let user_res = stmt.query_row(params![req.email, req.password], |row| row.get::<_, String>(0));

    match user_res {
        Ok(username) => {
            let token = generate_token(&username);
            HttpResponse::Ok().json(TokenResponse {
                token,
                message: "Login successful".to_string(),
            })
        }
        Err(_) => HttpResponse::Unauthorized().json(MessageResponse {
            message: "Invalid email or password".to_string(),
        }),
    }
}

#[post("/set_secret")]
async fn set_secret(
    req_http: HttpRequest,
    data: web::Data<Arc<DbState>>,
    req_body: web::Json<SecretRequest>,
) -> impl Responder {
    let auth_header = req_http.headers().get("Authorization");
    if let Some(auth_str) = auth_header.and_then(|h| h.to_str().ok()) {
        let token = auth_str.trim_start_matches("Bearer ");
        if verify_token(token, &req_body.username) {
            let mut conn = data.conn.lock().unwrap();
            conn.execute(
                "INSERT OR REPLACE INTO secrets (username, secret_value) VALUES (?1, ?2)",
                params![req_body.username, req_body.secret],
            ).expect("DB Error");
            
            return HttpResponse::Ok().json(MessageResponse {
                message: "Secret has been set successfully".to_string(),
            });
        }
    }
    HttpResponse::Unauthorized().json(MessageResponse {
        message: "Invalid authentication token".to_string(),
    })
}

#[get("/get_secret")]
async fn get_secret(
    req_http: HttpRequest,
    data: web::Data<Arc<DbState>>,
    query: web::Query<std::collections::HashMap<String, String>>,
) -> impl Responder {
    let username = match query.get("username") {
        Some(u) => u,
        None => return HttpResponse::BadRequest().finish(),
    };

    let auth_header = req_http.headers().get("Authorization");
    if let Some(auth_str) = auth_header.and_then(|h| h.to_str().ok()) {
        let token = auth_str.trim_start_matches("Bearer ");
        if verify_token(token, username) {
            let conn = data.conn.lock().unwrap();
            let res = conn.query_row(
                "SELECT secret_value FROM secrets WHERE username = ?1",
                params![username],
                |row| row.get::<_, String>(0),
            );

            match res {
                Ok(secret) => return HttpResponse::Ok().json(SecretResponse { secret }),
                Err(_) => return HttpResponse::NotFound().json(MessageResponse { message: "Secret not found".to_string() }),
            }
        }
    }
    HttpResponse::Unauthorized().json(MessageResponse {
        message: "Invalid authentication token".to_string(),
    })
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let db_conn = init_db();
    let state = Arc::new(DbState {
        conn: Mutex::new(db_conn),
    });

    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(state.clone()))
            .service(register)
            .service(login)
            .service(set_secret)
            .service(get_secret)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}