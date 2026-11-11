use actix_multipart::Multipart;
use actix_web::{
    get, post, web, App, HttpResponse, HttpServer, Responder,
};
use futures_util::{StreamExt, TryStreamExt};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::fs;
use std::io::Write;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use uuid::Uuid;

const STORAGE_DIR: &str = "uploads";

#[derive(Serialize)]
struct UploadResponse {
    id: String,
}

#[derive(Serialize)]
struct ErrorResponse {
    error: String,
}

struct AppState {
    db: Arc<Mutex<Connection>>,
}

fn init_db() -> Connection {
    let conn = Connection::open("images.db").expect("Failed to open database");
    conn.execute(
        "CREATE TABLE IF NOT EXISTS images (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            mime_type TEXT NOT NULL
        )",
        [],
    )
    .expect("Failed to create table");
    conn
}

#[post("/upload")]
async fn upload_image(mut payload: Multipart, data: web::Data<AppState>) -> impl Responder {
    let mut image_id = None;
    let mut mime_type = None;
    let mut file_path = None;

    while let Ok(Some(mut field)) = payload.try_next().await {
        if field.name() == "file" {
            let id = Uuid::new_v4().to_string();
            let content_type = field.content_type().map(|m| m.to_string()).unwrap_or_else(|| "application/octet-stream".to_string());
            
            let file_name = format!("{}.bin", id);
            let path = PathBuf::from(STORAGE_DIR).join(&file_name);
            
            let mut f = match fs::File::create(&path) {
                Ok(file) => file,
                Err(e) => return HttpResponse::InternalServerError().json(ErrorResponse { error: e.to_string() }),
            };

            while let Ok(Some(chunk)) = field.try_next().await {
                if let Err(e) = f.write_all(&chunk) {
                    return HttpResponse::InternalServerError().json(ErrorResponse { error: e.to_string() });
                }
            }

            // Save to DB
            let db = data.db.lock().unwrap();
            if let Err(e) = db.execute(
                "INSERT INTO images (id, filename, mime_type) VALUES (?1, ?2, ?3)",
                params![id, file_name, content_type],
            ) {
                return HttpResponse::InternalServerError().json(ErrorResponse { error: e.to_string() });
            }

            image_id = Some(id);
            mime_type = Some(content_type);
            file_path = Some(path);
        }
    }

    if let Some(id) = image_id {
        HttpResponse::Ok().json(UploadResponse { id })
    } else {
        HttpResponse::BadRequest().json(ErrorResponse { error: "Missing file field".to_string() })
    }
}

#[get("/images/{imageId}")]
async fn get_image(path: web::Path<String>, data: web::Data<AppState>) -> impl Responder {
    let image_id = path.into_inner();
    
    let db = data.db.lock().unwrap();
    let row: Result<(String, String), _> = db.query_row(
        "SELECT filename, mime_type FROM images WHERE id = ?1",
        params![image_id],
        |row| Ok((row.get(0)?, row.get(1)?)),
    );

    match row {
        Ok((filename, mime_type)) => {
            let full_path = PathBuf::from(STORAGE_DIR).join(filename);
            match fs::read(&full_path) {
                Ok(content) => {
                    // Use Content-Type to ensure browser renders it instead of downloading
                    // Content-Disposition is omitted to prevent download prompt
                    HttpResponse::Ok()
                        .content_type(mime_type.parse().unwrap_or_else(|_| "application/octet-stream".parse().unwrap()))
                        .body(content)
                }
                Err(_) => HttpResponse::NotFound().json(ErrorResponse { error: "File not found on disk".to_string() }),
            }
        }
        Err(_) => HttpResponse::NotFound().json(ErrorResponse { error: "Image not found".to_string() }),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();
    
    // Ensure upload directory exists
    fs::create_dir_all(STORAGE_DIR).expect("Could not create upload directory");

    let db_conn = init_db();
    let state = web::Data::new(AppState {
        db: Arc::new(Mutex::new(db_conn)),
    });

    println!("Server starting on 0.0.0.0:5000");
    HttpServer::new(move || {
        App::new()
            .app_data(state.clone())
            .service(upload_image)
            .service(get_image)
    })
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}