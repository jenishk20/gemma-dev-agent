use actix_multipart::Multipart;
use actix_web::{get, post, web, App, HttpResponse, HttpServer, Responder};
use futures_util::{StreamExt, TryStreamExt};
use serde::{Deserialize, Serialize};
use std::fs;
use std::io::Write;
use std::path::PathBuf;
use uuid::Uuid;

const UPLOAD_DIR: &str = "uploads";

#[derive(Serialize)]
struct UploadResponse {
    id: String,
}

#[derive(Serialize)]
struct ErrorResponse {
    error: String,
}

/// Handler for uploading images.
/// It processes a multipart stream, saves the file to disk, and returns a UUID.
#[post("/upload")]
async fn upload_image(mut payload: Multipart) -> impl Responder {
    let mut image_id = None;
    let mut content_type = String::new();

    // Iterate over the multipart stream
    while let Ok(Some(mut field)) = payload.try_next().await {
        // We only care about the field named "file" as per OpenAPI spec
        if field.name() == "file" {
            let id = Uuid::new_v4().to_string();
            
            // Extract content type to store it for later retrieval
            if let Some(ct) = field.content_type() {
                content_type = ct.to_string();
            } else {
                content_type = "application/octet-stream".to_string();
            }

            let file_path = PathBuf::from(UPLOAD_DIR).join(&id);
            let mut f = match fs::File::create(&file_path) {
                Ok(file) => file,
                Err(_) => return HttpResponse::InternalServerError().json(ErrorResponse { error: "Could not create file".into() }),
            };

            // Stream the body of the file to disk
            while let Ok(Some(chunk)) = field.try_next().await {
                if let Err(_) = f.write_all(&chunk) {
                    return HttpResponse::InternalServerError().json(ErrorResponse { error: "Failed to write file".into() });
                }
            }
            
            // Store the content type in a companion file to preserve it
            let ct_path = PathBuf::from(UPLOAD_DIR).join(format!("{}.mime", id));
            if let Err(_) = fs::write(ct_path, content_type) {
                return HttpResponse::InternalServerError().json(ErrorResponse { error: "Failed to save metadata".into() });
            }

            image_id = Some(id);
            break; // Only process the first 'file' field
        }
    }

    match image_id {
        Some(id) => HttpResponse::Ok().json(UploadResponse { id }),
        None => HttpResponse::BadRequest().json(ErrorResponse { error: "No file field provided".into() }),
    }
}

/// Handler for sharing images.
/// Reads the stored mime-type and serves the file with 'inline' disposition.
#[get("/images/{imageId}")]
async fn get_image(path: web::Path<String>) -> impl Responder {
    let image_id = path.into_inner();
    let file_path = PathBuf::from(UPLOAD_DIR).join(&image_id);
    let mime_path = PathBuf::from(UPLOAD_DIR).join(format!("{}.mime", image_id));

    if !file_path.exists() {
        return HttpResponse::NotFound().json(ErrorResponse { error: "Image not found".into() });
    }

    let content_type = match fs::read_to_string(mime_path) {
        Ok(ct) => ct,
        Err(_) => "application/octet-stream".to_string(),
    };

    match fs::read(&file_path) {
        Ok(content) => {
            // Content-Disposition: inline ensures the browser tries to render it rather than download it
            HttpResponse::Ok()
                .content_type(content_type)
                .insert_header(("Content-Disposition", "inline"))
                .body(content)
        }
        Err(_) => HttpResponse::InternalServerError().json(ErrorResponse { error: "Error reading file".into() }),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // Ensure upload directory exists
    fs::create_dir_all(UPLOAD_DIR)?;

    println!("Server starting on 0.0.0.0:5000...");
    HttpServer::new(|| {
        App::new()
            .service(upload_image)
            .service(get_image)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}