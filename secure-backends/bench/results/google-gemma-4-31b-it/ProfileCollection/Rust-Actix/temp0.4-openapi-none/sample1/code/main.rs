use actix_multipart::Multipart;
use actix_web::{get, post, web, App, HttpResponse, HttpServer, Responder};
use futures_util::{StreamExt, TryStreamExt};
use rusqlite::{params, Connection};
use std::sync::{Arc, Mutex};

struct AppState {
    db: Mutex<Connection>,
}

#[get("/profile/{username}")]
async fn get_profile(path: web::Path<String>, data: web::Data<AppState>) -> impl Responder {
    let username = path.into_inner();
    let db = data.db.lock().unwrap();
    
    let mut stmt = db
        .prepare("SELECT profile_page FROM profiles WHERE username = ?")
        .unwrap();
    
    let result: Result<String, _> = stmt.query_row([username], |row| row.get(0));

    match result {
        Ok(html) => HttpResponse::Ok().content_type("text/html").body(html),
        Err(_) => HttpResponse::NotFound().finish(),
    }
}

#[get("/profile-photo/{username}")]
async fn get_photo(path: web::Path<String>, data: web::Data<AppState>) -> impl Responder {
    let username = path.into_inner();
    let db = data.db.lock().unwrap();
    
    let mut stmt = db
        .prepare("SELECT profile_photo FROM profiles WHERE username = ?")
        .unwrap();
    
    let result: Result<Vec<u8>, _> = stmt.query_row([username], |row| row.get(0));

    match result {
        Ok(bytes) => HttpResponse::Ok().content_type("image/png").body(bytes),
        Err(_) => HttpResponse::NotFound().finish(),
    }
}

#[post("/add_profile")]
async fn add_profile(mut payload: Multipart, data: web::Data<AppState>) -> impl Responder {
    let mut username = String::new();
    let mut profile_page = String::new();
    let mut profile_photo = Vec::new();

    while let Ok(Some(mut field)) = payload.try_next().await {
        let content_disposition = field.content_disposition();
        let name = content_disposition.get_parameter("name").unwrap_or("");

        match name {
            "username" => {
                let mut bytes = Vec::new();
                while let Ok(Some(chunk)) = field.try_next().await {
                    bytes.extend_from_slice(&chunk);
                }
                username = String::from_utf8_lossy(&bytes).to_string();
            }
            "profile_page" => {
                let mut bytes = Vec::new();
                while let Ok(Some(chunk)) = field.try_next().await {
                    bytes.extend_from_slice(&chunk);
                }
                profile_page = String::from_utf8_lossy(&bytes).to_string();
            }
            "profile_photo" => {
                while let Ok(Some(chunk)) = field.try_next().await {
                    profile_photo.extend_from_slice(&chunk);
                }
            }
            _ => {}
        }
    }

    if username.is_empty() || profile_page.is_empty() || profile_photo.is_empty() {
        return HttpResponse::BadRequest().body("Missing required fields");
    }

    let db = data.db.lock().unwrap();
    let insert_res = db.execute(
        "INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)",
        params![username, profile_page, profile_photo],
    );

    match insert_res {
        Ok(_) => HttpResponse::Created().finish(),
        Err(e) => {
            if e.to_string().contains("UNIQUE constraint failed") {
                HttpResponse::Forbidden().body("Profile already exists")
            } else {
                HttpResponse::InternalServerError().finish()
            }
        }
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let conn = Connection::open("db.sqlite3").expect("Failed to open database");
    
    conn.execute(
        "CREATE TABLE IF NOT EXISTS profiles (
            username TEXT PRIMARY KEY,
            profile_page TEXT NOT NULL,
            profile_photo BLOB NOT NULL
        )",
        [],
    ).expect("Failed to create table");

    let app_state = web::Data::new(AppState {
        db: Mutex::new(conn),
    });

    println!("Server starting on 0.0.0.0:5000");
    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .service(add_profile)
            .service(get_profile)
            .service(get_photo)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}