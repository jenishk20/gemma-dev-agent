use actix_multipart::Multipart;
use actix_web::{post, App, HttpResponse, HttpServer, Responder};
use futures_util::StreamExt;
use std::io::Write;
use std::process::Command;
use tempdir::TempDir;
use uuid::Uuid;

#[post("/convert")]
async fn convert_pdf_to_text(mut payload: Multipart) -> impl Responder {
    // We only expect one file in the multipart form
    if let Some(result) = payload.next().await {
        match result {
            Ok(mut field) => {
                // Create a temporary directory to store the uploaded PDF and the resulting text
                let tmp_dir = match TempDir::new() {
                    Ok(dir) => dir,
                    Err(_) => return HttpResponse::InternalServerError().body("Failed to create temp directory"),
                };

                let file_id = Uuid::new_v4().to_string();
                let pdf_path = tmp_dir.path().join(format!("{}.pdf", file_id));
                let text_path = tmp_dir.path().join(format!("{}.txt", file_id));

                // Save the uploaded bytes to a file
                let mut f = match std::fs::File::create(&pdf_path) {
                    Ok(file) => file,
                    Err(_) => return HttpResponse::InternalServerError().body("Failed to create PDF file"),
                };

                while let Some(chunk) = field.next().await {
                    match chunk {
                        Ok(data) => {
                            if let Err(e) = f.write_all(&data) {
                                return HttpResponse::InternalServerError().body(format!("Error writing file: {}", e));
                            }
                        }
                        Err(e) => return HttpResponse::BadRequest().body(format!("Multipart error: {}", e)),
                    }
                }

                // Use pdftotext utility to extract text
                // pdftotext [options] <PDF-file> [text-file]
                let status = Command::new("pdftotext")
                    .arg(&pdf_path)
                    .arg(&text_path)
                    .status();

                match status {
                    Ok(s) if s.success() => {
                        // Read the resulting text file
                        match std::fs::read_to_string(&text_path) {
                            Ok(content) => HttpResponse::Ok().content_type("text/plain").body(content),
                            Err(_) => HttpResponse::InternalServerError().body("Failed to read converted text"),
                        }
                    }
                    Ok(_) => HttpResponse::InternalServerError().body("pdftotext utility failed to process the file"),
                    Err(e) => HttpResponse::InternalServerError().body(format!("Failed to execute pdftotext: {}", e)),
                }
            }
            Err(e) => HttpResponse::BadRequest().body(format!("Multipart error: {}", e)),
        }
    } else {
        HttpResponse::BadRequest().body("No file uploaded")
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();

    println!("Starting server on 0.0.0.0:5000...");
    HttpServer::new(|| {
        App::new().service(convert_pdf_to_text)
    })
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}