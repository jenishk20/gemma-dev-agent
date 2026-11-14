use actix_multipart::Multipart;
use actix_web::{get, post, web, App, HttpResponse, HttpServer, Responder};
use futures_util::{StreamExt, TryStreamExt};
use rusqlite::{params, Connection};
use std::sync::{Arc, Mutex};

struct AppState {
    db: Mutex<Connection>,
}

#[post("/add_profile")]
async fn add_profile(mut payload: Multipart, data: web::Data<AppState>) -> impl Responder {
    let mut username = None;
    let mut profile_page = None;
    let mut profile_photo = None;

    while let Ok(Some(mut field)) = payload.try_next().await {
        let content_disposition = field.content_disposition();
        let name = content_disposition.get_name().unwrap_or("");

        match name {
            "username" => {
                let mut bytes = Vec::new();
                while let Ok(Some(chunk)) = field.try_next().await {
                    bytes.extend_from_slice(&chunk);
                }
                username = Some(String::from_utf8_lossy(&bytes).into_owned());
            }
            "profile_page" => {
                let mut bytes = Vec::new();
                while let Ok(Some(chunk)) = field.try_next().await {
                    bytes.extend_from_slice(&chunk);
                }
                profile_page = Some(String::from_utf8_lossy(&bytes).into_owned());
            }
            "profile_photo" => {
                let mut bytes = Vec::new();
                while let Ok(Some(chunk)) = field.try_next().await {
                    bytes.extend_from_slice(&chunk);
                }
                profile_photo = Some(bytes);
            }
            _ => {}
        }
    }

    let username = match username {
        Some(u) if !u.is_empty() => u,
        _ => return HttpResponse::BadRequest().body("Missing username"),
    };
    let profile_page = match profile_page {
        Some(p) => p,
        _ => return HttpResponse::BadRequest().body("Missing profile page"),
    };
    let profile_photo = match profile_photo {
        Some(p) => p,
        _ => return HttpResponse::BadRequest().body("Missing profile photo"),
    };

    let db = data.db.lock().unwrap();
    let res = db.execute(
        "INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?1, ?2, ?3)",
        params![username, profile_page, profile_photo],
    );

    match res {
        Ok(_) => HttpResponse::Created().finish(),
        Err(e) => {
            if e.to_string().contains("UNIQUE constraint failed") {
                HttpResponse::Forbidden().body("Profile already exists")
            } else {
                HttpResponse::InternalServerError().body(e.to_string())
            }
        }
    }
}

#[get("/profile/{username}")]
async fn get_profile(path: web::Path<String>, data: web::Data<AppState>) -> impl Responder {
    let username = path.into_inner();
    let db = data.db.lock().unwrap();
    let mut stmt = db
        .prepare("SELECT profile_page FROM profiles WHERE username = ?1")
        .unwrap();
    
    let result = stmt.query_row(params![username], |row| row.get::<_, String>(0));

    match result {
        Ok(page) => HttpResponse::Ok().content_type("text/html").body(page),
        Err(_) => HttpResponse::NotFound().finish(),
    }
}

#[get("/profile-photo/{username}")]
async fn get_profile_photo(path: web::Path<String>, data: web::Data<AppState>) -> impl Responder {
    let username = path.into_inner();
    let db = data.db.lock().unwrap();
    let mut stmt = db
        .prepare("SELECT profile_photo FROM profiles WHERE username = ?1")
        .unwrap();

    let result = stmt.query_row(params![username], |row| row.get::<_, Vec<u8>>(0));

    match result {
        Ok(photo) => HttpResponse::Ok().content_type("image/png").body(photo),
        Err(_) => HttpResponse::NotFound().finish(),
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

    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .service(add_profile)
            .service(get_profile)
            .service(get_profile_photo)
    })
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}