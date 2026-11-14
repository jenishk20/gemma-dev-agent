use actix_web::{post, web, App, HttpResponse, HttpServer, Responder};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};
use uuid::Uuid;

// --- Models ---

#[derive(Deserialize)]
struct InviteRequest {
    email: String,
}

#[derive(Serialize)]
struct InviteResponse {
    invite_id: String,
    message: String,
}

#[derive(Deserialize)]
struct CreateUserRequest {
    invite_id: String,
    user_name: String,
    password: String,
}

#[derive(Serialize)]
struct MessageResponse {
    message: String,
}

// --- Database State ---

struct AppState {
    db: Mutex<Connection>,
}

// Initialize the SQLite database
fn init_db() -> Connection {
    let conn = Connection::open("db.sqlite3").expect("Failed to open database");
    
    conn.execute(
        "CREATE TABLE IF NOT EXISTS invitations (
            invite_id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            used INTEGER DEFAULT 0
        )",
        [],
    ).expect("Failed to create invitations table");

    conn.execute(
        "CREATE TABLE IF NOT EXISTS users (
            user_name TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            email TEXT NOT NULL
        )",
        [],
    ).expect("Failed to create users table");

    conn
}

// --- Handlers ---

#[post("/invite_user")]
async fn invite_user(data: web::Data<AppState>, req: web::Json<InviteRequest>) -> impl Responder {
    let mut conn = data.db.lock().unwrap();
    let email = req.email.clone();

    // Check if invitation already exists for this email
    let existing: Result<String, rusqlite::Error> = conn.query_row(
        "SELECT invite_id FROM invitations WHERE email = ?1",
        params![email],
        |row| row.get(0),
    );

    if let Ok(invite_id) = existing {
        return HttpResponse::Ok().json(InviteResponse {
            invite_id,
            message: "Invitation already exists.".to_string(),
        });
    }

    // Create new invitation
    let invite_id = Uuid::new_v4().to_string();
    let res = conn.execute(
        "INSERT INTO invitations (invite_id, email) VALUES (?1, ?2)",
        params![invite_id, email],
    );

    match res {
        Ok(_) => HttpResponse::Ok().json(InviteResponse {
            invite_id,
            message: "Invitation created successfully.".to_string(),
        }),
        Err(_) => HttpResponse::InternalServerError().json(MessageResponse {
            message: "Database error occurred.".to_string(),
        }),
    }
}

#[post("/create_user")]
async fn create_user(data: web::Data<AppState>, req: web::Json<CreateUserRequest>) -> impl Responder {
    let mut conn = data.db.lock().unwrap();

    // 1. Validate invite_id and get associated email
    let invite_info: Result<(String, i32), rusqlite::Error> = conn.query_row(
        "SELECT email, used FROM invitations WHERE invite_id = ?1",
        params![req.invite_id],
        |row| Ok((row.get(0)?, row.get(1)?)),
    );

    let (email, used) = match invite_info {
        Ok(info) => info,
        Err(_) => return HttpResponse::Unauthorized().json(MessageResponse {
            message: "Invalid invite_id".to_string(),
        }),
    };

    if used == 1 {
        return HttpResponse::Unauthorized().json(MessageResponse {
            message: "Invitation has already been used".to_string(),
        });
    }

    // 2. Check if username already exists
    let user_exists: Result<i32, rusqlite::Error> = conn.query_row(
        "SELECT COUNT(*) FROM users WHERE user_name = ?1",
        params![req.user_name],
        |row| row.get(0),
    );

    if let Ok(count) = user_exists {
        if count > 0 {
            return HttpResponse::BadRequest().json(MessageResponse {
                message: "Username already exists. Try providing different username.".to_string(),
            });
        }
    }

    // 3. Create user and mark invitation as used
    // Using a transaction to ensure atomicity
    let tx = match conn.transaction() {
        Ok(t) => t,
        Err(_) => return HttpResponse::InternalServerError().finish(),
    };

    let user_res = tx.execute(
        "INSERT INTO users (user_name, password, email) VALUES (?1, ?2, ?3)",
        params![req.user_name, req.password, email],
    );

    if user_res.is_err() {
        return HttpResponse::InternalServerError().json(MessageResponse {
            message: "Failed to create user".to_string(),
        });
    }

    let invite_res = tx.execute(
        "UPDATE invitations SET used = 1 WHERE invite_id = ?1",
        params![req.invite_id],
    );

    if invite_res.is_err() {
        return HttpResponse::InternalServerError().json(MessageResponse {
            message: "Failed to mark invitation as used".to_string(),
        });
    }

    if tx.commit().is_err() {
        return HttpResponse::InternalServerError().finish();
    }

    HttpResponse::Ok().json(MessageResponse {
        message: "User created".to_string(),
    })
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init_from_env(env_logger::Env::new().default_filter_or("info"));

    let db_conn = init_db();
    let state = web::Data::new(AppState {
        db: Mutex::new(db_conn),
    });

    println!("Server starting on 0.0.0.0:5000");
    HttpServer::new(move || {
        App::new()
            .app_data(state.clone())
            .service(invite_user)
            .service(create_user)
    })
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}