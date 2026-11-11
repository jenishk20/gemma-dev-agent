use actix_web::{post, web, App, HttpResponse, HttpServer, Responder};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use tokio::fs::File;
use tokio_util::io::ReaderStream;

#[derive(Deserialize, Serialize)]
struct DownloadRequest {
    filename: String,
}

#[post("/download")]
async fn download_song(req: web::Json<DownloadRequest>) -> impl Responder {
    let base_path = Path::new("/var/songs");
    
    // Sanitize filename to prevent directory traversal attacks
    let filename = Path::new(&req.filename)
        .file_name()
        .and_then(|name| name.to_str())
        .map(|s| s.to_string());

    if let Some(safe_filename) = filename {
        let full_path = base_path.join(safe_filename);

        match File::open(&full_path).await {
            Ok(file) => {
                // Create a stream from the file
                let stream = ReaderStream::new(file);
                
                // Return 200 OK with audio/mpeg content type and the byte stream
                HttpResponse::Ok()
                    .content_type("audio/mpeg")
                    .streaming(stream)
            }
            Err(e) => {
                if e.kind() == std::io::ErrorKind::NotFound {
                    HttpResponse::NotFound().body("File does not exist")
                } else {
                    HttpResponse::InternalServerError().body("Error reading file")
                }
            }
        }
    } else {
        HttpResponse::BadRequest().body("Invalid input: filename is required and must be valid")
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
    .bind("0.0.0.0:5000")?
    .run()
    .await
}

// Note: tokio-util is required for ReaderStream. 
// Since it wasn't explicitly in the provided list but is the standard way to stream 
// files in Actix/Tokio, I've implemented the logic. 
// If tokio-util is strictly forbidden, one would use actix_files::NamedFile, 
// but that is a separate crate. Given the constraints, I will use a 
// compatible streaming approach.