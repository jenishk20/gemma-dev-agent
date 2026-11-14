use actix_web::{post, web, App, HttpResponse, HttpServer, Responder};
use serde::Deserialize;
use std::path::PathBuf;
use tokio::fs::File;
use tokio_util::codec::{BytesCodec, FramedRead};

#[derive(Deserialize)]
struct DownloadRequest {
    filename: String,
}

#[post("/download")]
async fn download_song(req: web::Json<DownloadRequest>) -> impl Responder {
    // Sanitize filename to prevent directory traversal attacks
    let filename = req.filename.clone();
    let sanitized_filename = match std::path::Path::new(&filename)
        .file_name()
    {
        Some(name) => name.to_str().unwrap_or(""),
        None => return HttpResponse::BadRequest().body("Invalid filename"),
    };

    if sanitized_filename.is_empty() {
        return HttpResponse::BadRequest().body("Invalid filename");
    }

    // Construct path to /var/songs
    let mut path = PathBuf::from("/var/songs");
    path.push(sanitized_filename);

    // Attempt to open the file
    match File::open(&path).await {
        Ok(file) => {
            // Create a stream from the file
            let stream = FramedRead::new(file, BytesCodec::new());
            
            // Return the stream with the correct content type
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