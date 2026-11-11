use actix_multipart::Multipart;
use actix_web::{
    get, post, web, App, HttpResponse, HttpServer, Responder,
};
use futures_util::StreamExt;
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

/// Initialize the upload directory on startup
async fn init_storage() -> std::io::Result<()> {
    if !std::path::Path::new(UPLOAD_DIR).exists() {
        fs::create_dir_all(UPLOAD_DIR)?;
    }
    Ok(())
}

#[post("/upload")]
async fn upload_image(mut payload: Multipart) -> impl Responder {
    let mut file_id = String::new();
    let mut content_type = String::new();
    let mut file_data = Vec::new();

    // Iterate over multipart sections
    while let Some(item) = payload.next().await {
        match item {
            Ok(mut field) => {
                // We only care about the 'file' field as per OpenAPI spec
                if field.name() == "file" {
                    while let Some(chunk) = field.next().await {
                        match chunk {
                            Ok(data) => file_data.extend_from_slice(&data),
                            Err(_) => return HttpResponse::InternalServerError().json(ErrorResponse { error: "Error reading chunk".to_string() }),
                        }
                    }
                    
                    // Extract content type from the field headers
                    content_type = field
                        .content_type()
                        .map(|ct| ct.to_string())
                        .unwrap_or_else(|| "application/octet-stream".to_string());
                }
            }
            Err(_) => return HttpResponse::BadRequest().json(ErrorResponse { error: "Invalid multipart data".to_string() }),
        }
    }

    if file_data.is_empty() {
        return HttpResponse::BadRequest().json(ErrorResponse { error: "No file uploaded".to_string() });
    }

    // Generate a unique ID and save the file
    let id = Uuid::new_v4().to_string();
    let file_path = PathBuf::from(UPLOAD_DIR).join(&id);

    match fs::File::create(&file_path) {
        Ok(mut f) => {
            if let Err(e) = f.write_all(&file_data) {
                return HttpResponse::InternalServerError().json(ErrorResponse { error: e.to_string() });
            }
            file_id = id;
        }
        Err(e) => return HttpResponse::InternalServerError().json(ErrorResponse { error: e.to_string() }),
    }

    // Store the content type in a sidecar file to preserve it for the GET request
    let meta_path = PathBuf::from(UPLOAD_DIR).join(format!("{}.mime", file_id));
    if let Err(e) = fs::write(meta_path, content_type) {
        return HttpResponse::InternalServerError().json(ErrorResponse { error: e.to_string() });
    }

    HttpResponse::Ok().json(UploadResponse { id: file_id })
}

#[get("/images/{imageId}")]
async fn get_image(path: web::Path<String>) -> impl Responder {
    let image_id = path.into_inner();
    let file_path = PathBuf::from(UPLOAD_DIR).join(&image_id);
    let meta_path = PathBuf::from(UPLOAD_DIR).join(format!("{}.mime", image_id));

    if !file_path.exists() {
        return HttpResponse::NotFound().json(ErrorResponse { error: "Image not found".to_string() });
    }

    // Read the preserved mime type
    let mime_type = fs::read_to_string(meta_path).unwrap_or_else(|_| "application/octet-stream".to_string());

    match fs::read(&file_path) {
        Ok(content) => {
            // Use inline content-disposition to ensure browser views it rather than downloading
            HttpResponse::Ok()
                .content_type(mime_type)
                .insert_header(("Content-Disposition", "inline"))
                .body(content)
        }
        Err(e) => HttpResponse::InternalServerError().json(ErrorResponse { error: e.to_string() }),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // Ensure upload directory exists
    init_storage().await?;

    println!("Server starting on 0.0.0.0:5000");
    HttpServer::new(|| {
        App::new()
            .service(upload_image)
            .service(get_image)
    })
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}