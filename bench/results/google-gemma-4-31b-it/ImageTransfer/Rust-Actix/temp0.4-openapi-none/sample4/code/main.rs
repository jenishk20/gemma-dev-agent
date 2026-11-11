use actix_multipart::Multipart;
use actix_web::{get, post, web, App, HttpResponse, HttpServer, Responder};
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

/// Handler for uploading images.
/// It processes a multipart stream and saves the file to the local filesystem.
#[post("/upload")]
async fn upload_image(mut payload: Multipart) -> impl Responder {
    let mut file_id = String::new();
    let mut content_type = String::new();
    let mut bytes_written = 0;

    // Iterate over multipart sections
    while let Some(item) = payload.next().await {
        let mut field = match item {
            Ok(f) => f,
            Err(_) => return HttpResponse::BadRequest().json(ErrorResponse { error: "Invalid multipart data".into() }),
        };

        // We only care about the "file" field as per OpenAPI spec
        if field.name() == "file" {
            file_id = Uuid::new_v4().to_string();
            content_type = field.content_type().map(|ct| ct.to_string()).unwrap_or_else(|| "application/octet-stream".to_string());
            
            // Extract filename or default to "image"
            let filename = field.content_disposition().get_filename().unwrap_or("image");
            let extension = PathBuf::from(filename).extension().and_then(|e| e.to_str()).unwrap_or("bin");
            let full_path = format!("{}/{}.{}", UPLOAD_DIR, file_id, extension);

            let mut f = match fs::File::create(&full_path) {
                Ok(file) => file,
                Err(e) => return HttpResponse::InternalServerError().json(ErrorResponse { error: e.to_string() }),
            };

            while let Some(chunk) = field.next().await {
                let data = match chunk {
                    Ok(d) => d,
                    Err(_) => return HttpResponse::InternalServerError().json(ErrorResponse { error: "Error reading stream".into() }),
                };
                if let Err(e) = f.write_all(&data) {
                    return HttpResponse::InternalServerError().json(ErrorResponse { error: e.to_string() });
                }
                bytes_written += data.len();
            }
            
            // Store the content type in a sidecar file to preserve it for the GET request
            let meta_path = format!("{}/{}.meta", UPLOAD_DIR, file_id);
            if let Err(e) = fs::write(meta_path, content_type) {
                return HttpResponse::InternalServerError().json(ErrorResponse { error: e.to_string() });
            }
        }
    }

    if bytes_written == 0 {
        return HttpResponse::BadRequest().json(ErrorResponse { error: "No file uploaded".into() });
    }

    HttpResponse::Ok().json(UploadResponse { id: file_id })
}

/// Handler for serving images.
/// It looks for the file and its associated metadata to set the correct Content-Type.
#[get("/images/{imageId}")]
async fn get_image(path: web::Path<String>) -> impl Responder {
    let image_id = path.into_inner();
    let meta_path = format!("{}/{}.meta", UPLOAD_DIR, image_id);
    
    // Find the file associated with this ID (since we don't know the extension)
    let entries = match fs::read_dir(UPLOAD_DIR) {
        Ok(e) => e,
        Err(_) => return HttpResponse::InternalServerError().json(ErrorResponse { error: "Storage error".into() }),
    };

    let mut target_file = None;
    for entry in entries.flatten() {
        let path = entry.path();
        if path.file_name().and_then(|n| n.to_str()).map_or(false, |n| n.starts_with(&image_id) && !n.ends_with(".meta")) {
            target_file = Some(path);
            break;
        }
    }

    let file_path = match target_file {
        Some(p) => p,
        None => return HttpResponse::NotFound().json(ErrorResponse { error: "Image not found".into() }),
    };

    // Retrieve original mime type from meta file
    let mime = match fs::read_to_string(meta_path) {
        Ok(m) => m,
        Err(_) => "application/octet-stream".to_string(),
    };

    match fs::read(&file_path) {
        Ok(content) => {
            // "inline" disposition ensures it's viewed in browser, not downloaded
            HttpResponse::Ok()
                .content_type(mime)
                .insert_header(("Content-Disposition", "inline"))
                .body(content)
        }
        Err(e) => HttpResponse::InternalServerError().json(ErrorResponse { error: e.to_string() }),
    }
}

#[tokio::main]
async fn main() -> std::io::Result<()> {
    // Ensure upload directory exists
    fs::create_dir_all(UPLOAD_DIR)?;

    println!("Starting server at http://0.0.0.0:5000");
    HttpServer::new(|| {
        App::new()
            .service(upload_image)
            .service(get_image)
    })
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}