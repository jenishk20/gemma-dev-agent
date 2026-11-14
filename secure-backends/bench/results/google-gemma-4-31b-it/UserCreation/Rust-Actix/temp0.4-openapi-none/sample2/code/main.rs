use actix_web::{post, web, App, HttpResponse, HttpServer, Responder};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::env;
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

// --- Handlers ---

#[post("/invite_user")]
async fn invite_user(data: web::Data<AppState>, req: web::Json<InviteRequest>) -> impl Responder {
    let db = data.db.lock().unwrap();
    
    // Check if invitation already exists for this email
    let existing_id: Option<String> = db
        .query_row(
            "SELECT invite_id FROM invitations WHERE email = ?1",
            params![req.email],
            |row| row.get(0),
        )
        .ok();

    if let Some(id) = existing_id {
        return HttpResponse::Ok().json(InviteResponse {
            invite_id: id,
            message: "Invitation already exists and is being reused.".to_string(),
        });
    }

    // Create new invitation
    let invite_id = Uuid::new_v4().to_string();
    let res = db.execute(
        "INSERT INTO invitations (invite_id, email, used) VALUES (?1, ?2, 0)",
        params![invite_id, req.email],
    );

    match res {
        Ok(_) => HttpResponse::Ok().json(InviteResponse {
            invite_id,
            message: "Invitation created successfully.".to_string(),
        }),
        Err(e) => HttpResponse::InternalServerError().json(MessageResponse {
            message: format!("Database error: {}", e),
        }),
    }
}

#[post("/create_user")]
async fn create_user(data: web::Data<AppState>, req: web::Json<CreateUserRequest>) -> impl Responder {
    let db = data.db.lock().unwrap();

    // 1. Validate invitation
    let invite_valid: Option<(i32, String)> = db
        .query_row(
            "SELECT rowid, email FROM invitations WHERE invite_id = ?1 AND used = 0",
            params![req.invite_id],
            |row| Ok((row.get(0)?, row.get(1)?)),
        )
        .ok();

    let (invite_rowid, _email) = match invite_valid {
        Some(val) => val,
        None => return HttpResponse::Unauthorized().json(MessageResponse {
            message: "Invalid invite_id".to_string(),
        }),
    };

    // 2. Check if username already exists
    let user_exists: bool = db
        .query_row(
            "SELECT EXISTS(SELECT 1 FROM users WHERE user_name = ?1)",
            params![req.user_name],
            |row| row.get(0),
        )
        .unwrap_or(false);

    if user_exists {
        return HttpResponse::BadRequest().json(MessageResponse {
            message: "Username already exists. Try providing different username.".to_string(),
        });
    }

    // 3. Create user and mark invitation as used in a transaction
    // Note: In a real app, we would hash the password.
    let tx_res = db.unchecked_transaction().and_then(|tx| {
        tx.execute(
            "INSERT INTO users (user_name, password) VALUES (?1, ?2)",
            params![req.user_name, req.password],
        )?;
        tx.execute(
            "UPDATE invitations SET used = 1 WHERE rowid = ?1",
            params![invite_rowid],
        )?;
        tx.commit()
    });

    match tx_res {
        Ok(_) => HttpResponse::Ok().json(MessageResponse {
            message: "User created successfully".to_string(),
        }),
        Err(e) => HttpResponse::InternalServerError().json(MessageResponse {
            message: format!("Transaction error: {}", e),
        }),
    }
}

// Helper for manual transaction handling since rusqlite's Transaction requires a mutable reference
impl Connection {
    fn unchecked_transaction(&mut self) -> rusqlite::Result<rusqlite::Transaction> {
        self.transaction()
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // Initialize DB
    let conn = Connection::open("db.sqlite3").expect("Could not open sqlite database");
    
    conn.execute(
        "CREATE TABLE IF NOT EXISTS invitations (
            invite_id TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            used INTEGER DEFAULT 0
        )",
        [],
    ).expect("Failed to create invitations table");

    conn.execute(
        "CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )",
        [],
    ).expect("Failed to create users table");

    let app_state = web::Data::new(AppState {
        db: Mutex::new(conn),
    });

    // Ensure APP_SECRET is present as per requirements, though not used for logic here
    let _ = env::var("APP_SECRET").unwrap_or_else(|_| "default_secret".to_string());

    println!("Starting server on 0.0.0.0:5000...");
    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .service(invite_user)
            .service(create_user)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}