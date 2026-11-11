use actix_web::{post, web, App, HttpResponse, HttpServer, Responder};
use serde::{Deserialize, Serialize};
use tokio::fs::File;
use tokio_util::io::ReaderStream;
use std::path::Path;

#[derive(Deserialize, Serialize)]
struct DownloadRequest {
    filename: String,
}

#[post("/download")]
async fn download_song(req: web::Json<DownloadRequest>) -> impl Responder {
    let base_path = "/var/songs";
    
    // Basic security check to prevent directory traversal attacks
    // Ensure the filename doesn't contain path separators
    if req.filename.contains('/') || req.filename.contains('\\') || req.filename.contains("..") {
        return HttpResponse::BadRequest().body("Invalid filename provided");
    }

    let full_path = Path::new(base_path).join(&req.filename);

    // Attempt to open the file
    match File::open(&full_path).await {
        Ok(file) => {
            // Create a stream from the file
            let stream = ReaderStream::new(file);
            
            // Return the stream with the correct content type
            HttpResponse::Ok()
                .content_type("audio/mpeg")
                .streaming(stream)
        }
        Err(e) => {
            match e.kind() {
                std::io::ErrorKind::NotFound => HttpResponse::NotFound().body("File does not exist"),
                _ => HttpResponse::InternalServerError().body("An error occurred while accessing the file"),
            }
        }
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();
    
    println!("Starting server on 0.0.0.0:5000...");
    
    HttpServer::new(|| {
        App::new()
            .service(download_song)
    })
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}