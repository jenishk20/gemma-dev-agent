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

// --- Database Logic ---

struct DbState {
    conn: Mutex<Connection>,
}

fn init_db() -> Connection {
    let conn = Connection::open("db.sqlite3").expect("Failed to open database");
    conn.execute(
        "CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL
        )",
        [],
    ).expect("Failed to create users table");
    conn
}

// --- Handlers ---

#[post("/register")]
async fn register(data: web::Data<Arc<DbState>>, req: web::Json<RegisterRequest>) -> impl Responder {
    let mut conn = data.conn.lock().unwrap();
    let user_id = uuid::Uuid::new_v4().to_string();

    let result = conn.execute(
        "INSERT INTO users (id, email, password, name) VALUES (?1, ?2, ?3, ?4)",
        params![user_id, req.email, req.password, req.name],
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
async fn login(data: web::Data<Arc<DbState>>, req: web::Json<LoginRequest>) -> impl Responder {
    let conn = data.conn.lock().unwrap();
    let mut stmt = conn
        .prepare("SELECT id FROM users WHERE email = ?1 AND password = ?2")
        .unwrap();
    
    let user_res = stmt.query_row(params![req.email, req.password], |row| {
        let id: String = row.get(0)?;
        Ok(id)
    });

    match user_res {
        Ok(user_id) => {
            let secret = env::var("APP_SECRET").unwrap_or_else(|_| "default_secret".to_string());
            // In a real app, we would sign a JWT. Here we simulate a token using the secret and user_id.
            let token = format!("jwt-token-{}-{}", secret, user_id);
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

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();

    let db_conn = init_db();
    let state = Arc::new(DbState {
        conn: Mutex::new(db_conn),
    });

    println!("Starting server on 0.0.0.0:5000");
    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(state.clone()))
            .service(register)
            .service(login)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}