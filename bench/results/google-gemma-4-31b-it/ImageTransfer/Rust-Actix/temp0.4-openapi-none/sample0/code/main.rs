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
/// It processes a multipart stream and saves the file to the local disk.
#[post("/upload")]
async fn upload_image(mut payload: Multipart) -> impl Responder {
    // Ensure upload directory exists
    if let Err(e) = fs::create_dir_all(UPLOAD_DIR) {
        return HttpResponse::InternalServerError().json(ErrorResponse {
            error: format!("Failed to create upload directory: {}", e),
        });
    }

    // We only expect one file based on the schema
    if let Some(result) = payload.next().await {
        match result {
            Ok(mut field) => {
                let content_type = field
                    .content_type()
                    .map(|ct| ct.to_string())
                    .unwrap_or_else(|| "application/octet-stream".to_string());
                
                let file_id = Uuid::new_v4().to_string();
                let file_path = PathBuf::from(UPLOAD_DIR).join(&file_id);

                // Create the file
                let mut f = match fs::File::create(&file_path) {
                    Ok(file) => file,
                    Err(e) => return HttpResponse::InternalServerError().json(ErrorResponse { error: e.to_string() }),
                };

                // Stream the body to the file
                while let Some(chunk) = field.next().await {
                    match chunk {
                        Ok(data) => {
                            if let Err(e) = f.write_all(&data) {
                                return HttpResponse::InternalServerError().json(ErrorResponse { error: e.to_string() });
                            }
                        }
                        Err(e) => return HttpResponse::BadRequest().json(ErrorResponse { error: e.to_string() }),
                    }
                }

                // Store the mime type in a companion file to preserve it for the GET request
                let mime_path = file_path.with_extension("mime");
                if let Err(e) = fs::write(mime_path, content_type) {
                    return HttpResponse::InternalServerError().json(ErrorResponse { error: e.to_string() });
                }

                return HttpResponse::Ok().json(UploadResponse { id: file_id });
            }
            Err(e) => return HttpResponse::BadRequest().json(ErrorResponse { error: e.to_string() }),
        }
    }

    HttpResponse::BadRequest().json(ErrorResponse {
        error: "No file provided in request".to_string(),
    })
}

/// Handler for serving images.
/// It reads the stored mime type and returns the file as an inline response.
#[get("/images/{imageId}")]
async fn get_image(path: web::Path<String>) -> impl Responder {
    let image_id = path.into_inner();
    let file_path = PathBuf::from(UPLOAD_DIR).join(&image_id);
    let mime_path = file_path.with_extension("mime");

    if !file_path.exists() {
        return HttpResponse::NotFound().json(ErrorResponse {
            error: "Image not found".to_string(),
        });
    }

    // Retrieve the original mime type
    let content_type = match fs::read_to_string(mime_path) {
        Ok(ct) => ct,
        Err(_) => "application/octet-stream".to_string(),
    };

    match fs::read(&file_path) {
        Ok(content) => {
            // "inline" content-disposition ensures the browser tries to render it rather than download it
            HttpResponse::Ok()
                .content_type(content_type)
                .insert_header(("Content-Disposition", "inline"))
                .body(content)
        }
        Err(e) => HttpResponse::InternalServerError().json(ErrorResponse {
            error: e.to_string(),
        }),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init_from_env(env_logger::Env::new().default_filter_or("info"));

    println!("Starting server on 0.0.0.0:5000...");
    
    HttpServer::new(|| {
        App::new()
            .service(upload_image)
            .service(get_image)
    })
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}