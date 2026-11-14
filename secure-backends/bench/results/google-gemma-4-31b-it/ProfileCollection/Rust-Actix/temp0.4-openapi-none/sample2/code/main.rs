use actix_multipart::Multipart;
use actix_web::{get, post, web, App, HttpResponse, HttpServer, Responder};
use futures_util::{StreamExt, TryStreamExt};
use rusqlite::{params, Connection};
use std::sync::{Arc, Mutex};

struct AppState {
    db: Mutex<Connection>,
}

async fn init_db() -> Connection {
    let conn = Connection::open("db.sqlite3").expect("Failed to open database");
    conn.execute(
        "CREATE TABLE IF NOT EXISTS profiles (
            username TEXT PRIMARY KEY,
            profile_page TEXT NOT NULL,
            profile_photo BLOB NOT NULL
        )",
        [],
    )
    .expect("Failed to create table");
    conn
}

#[post("/add_profile")]
async fn add_profile(
    state: web::Data<AppState>,
    mut payload: Multipart,
) -> impl Responder {
    let mut username = None;
    let mut profile_page = None;
    let mut profile_photo = None;

    while let Ok(Some(mut field)) = payload.try_next().await {
        let content_disposition = field.content_disposition();
        let name = content_disposition
            .get_parameter("name")
            .unwrap_or("unknown")
            .to_string();

        match name.as_str() {
            "username" => {
                let mut bytes = web::BytesMut::new();
                while let Ok(Some(chunk)) = field.try_next().await {
                    bytes.extend_from_slice(&chunk);
                }
                username = Some(String::from_utf8_lossy(&bytes).to_string());
            }
            "profile_page" => {
                let mut bytes = web::BytesMut::new();
                while let Ok(Some(chunk)) = field.try_next().await {
                    bytes.extend_from_slice(&chunk);
                }
                profile_page = Some(String::from_utf8_lossy(&bytes).to_string());
            }
            "profile_photo" => {
                let mut bytes = web::BytesMut::new();
                while let Ok(Some(chunk)) = field.try_next().await {
                    bytes.extend_from_slice(&chunk);
                }
                profile_photo = Some(bytes.to_vec());
            }
            _ => {}
        }
    }

    if let (Some(u), Some(p), Some(ph)) = (username, profile_page, profile_photo) {
        let db = state.db.lock().unwrap();
        match db.execute(
            "INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?1, ?2, ?3)",
            params![u, p, ph],
        ) {
            Ok(_) => return HttpResponse::Created().finish(),
            Err(e) => {
                if e.to_string().contains("UNIQUE constraint failed") {
                    return HttpResponse::Forbidden().body("Profile already exists");
                }
                return HttpResponse::BadRequest().body("Database error");
            }
        }
    }

    HttpResponse::BadRequest().body("Invalid input: missing fields")
}

#[get("/profile/{username}")]
async fn get_profile(state: web::Data<AppState>, path: web::Path<String>) -> impl Responder {
    let username = path.into_inner();
    let db = state.db.lock().unwrap();
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
async fn get_profile_photo(state: web::Data<AppState>, path: web::Path<String>) -> impl Responder {
    let username = path.into_inner();
    let db = state.db.lock().unwrap();
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
    let db_conn = init_db().await;
    let app_state = web::Data::new(AppState {
        db: Mutex::new(db_conn),
    });

    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .service(add_profile)
            .service(get_profile)
            .service(get_profile_photo)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}