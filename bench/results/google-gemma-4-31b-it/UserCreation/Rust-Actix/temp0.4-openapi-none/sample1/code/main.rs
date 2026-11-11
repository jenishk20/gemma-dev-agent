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

struct AppState {
    db: Mutex<Connection>,
}

// --- Database Initialization ---

fn init_db() -> Connection {
    let conn = Connection::open("db.sqlite3").expect("Failed to open database");
    
    conn.execute(
        "CREATE TABLE IF NOT EXISTS invitations (
            invite_id TEXT PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
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
async fn invite_user(
    data: web::Data<Arc<AppState>>,
    req: web::Json<InviteRequest>,
) -> impl Responder {
    let db = data.db.lock().unwrap();
    let email = &req.email;

    // Check if invitation already exists for this email
    let existing_id: Option<String> = db
        .query_row(
            "SELECT invite_id FROM invitations WHERE email = ?1",
            params![email],
            |row| row.get(0),
        )
        .ok();

    if let Some(id) = existing_id {
        return HttpResponse::Ok().json(InviteResponse {
            invite_id: id,
            message: "Invitation already exists for this email.".to_string(),
        });
    }

    // Create new invitation
    let invite_id = Uuid::new_v4().to_string();
    let res = db.execute(
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
async fn create_user(
    data: web::Data<Arc<AppState>>,
    req: web::Json<CreateUserRequest>,
) -> impl Responder {
    let db = data.db.lock().unwrap();

    // 1. Validate invite_id and get associated email
    let invite_info: Option<(String, i32)> = db
        .query_row(
            "SELECT email, used FROM invitations WHERE invite_id = ?1",
            params![req.invite_id],
            |row| Ok((row.get(0)?, row.get(1)?)),
        )
        .ok();

    let (email, used) = match invite_info {
        Some((email, used)) if used == 0 => (email, used),
        _ => {
            return HttpResponse::Unauthorized().json(MessageResponse {
                message: "Invalid invite_id".to_string(),
            });
        }
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

    // 3. Create user and mark invitation as used
    // Using a transaction for atomicity
    let tx = match db.unchecked_transaction() {
        Ok(tx) => tx,
        Err(_) => return HttpResponse::InternalServerError().finish(),
    };

    let user_res = tx.execute(
        "INSERT INTO users (user_name, password, email) VALUES (?1, ?2, ?3)",
        params![req.user_name, req.password, email],
    );

    let invite_res = tx.execute(
        "UPDATE invitations SET used = 1 WHERE invite_id = ?1",
        params![req.invite_id],
    );

    if user_res.is_ok() && invite_res.is_ok() {
        tx.commit().expect("Failed to commit transaction");
        HttpResponse::Ok().json(MessageResponse {
            message: "User created".to_string(),
        })
    } else {
        HttpResponse::InternalServerError().json(MessageResponse {
            message: "Failed to create user".to_string(),
        })
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // Load APP_SECRET if needed (though not explicitly used in logic, requested by prompt)
    let _secret = env::var("APP_SECRET").unwrap_or_else(|_| "default_secret".to_string());

    let db_conn = init_db();
    let state = Arc::new(AppState {
        db: Mutex::new(db_conn),
    });

    println!("Server starting on 0.0.0.0:5000...");
    
    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(state.clone()))
            .service(invite_user)
            .service(create_user)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}