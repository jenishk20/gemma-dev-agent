use actix_multipart::Multipart;
use actix_web::{post, App, HttpResponse, HttpServer, Responder};
use futures_util::StreamExt;
use std::fs::File;
use std::io::Write;
use std::process::Command;
use tempdir::TempDir;

#[post("/convert")]
async fn convert_pdf_to_text(mut payload: Multipart) -> impl Responder {
    // Iterate over the multipart stream
    while let Some(item) = payload.next().await {
        match item {
            Ok(mut field) => {
                // We only care about the field named "file"
                if field.name() == "file" {
                    // Create a temporary directory to store the uploaded PDF
                    let tmp_dir = match TempDir::new() {
                        Ok(dir) => dir,
                        Err(_) => return HttpResponse::InternalServerError().body("Failed to create temp directory"),
                    };

                    let input_path = tmp_dir.path().join("input.pdf");
                    let output_path = tmp_dir.path().join("output.txt");

                    // Write the multipart stream to the temporary file
                    let mut f = match File::create(&input_path) {
                        Ok(file) => file,
                        Err(_) => return HttpResponse::InternalServerError().body("Failed to create input file"),
                    };

                    while let Some(chunk) = field.next().await {
                        match chunk {
                            Ok(data) => {
                                if let Err(_) = f.write_all(&data) {
                                    return HttpResponse::InternalServerError().body("Failed to write file data");
                                }
                            }
                            Err(_) => return HttpResponse::BadRequest().body("Error reading multipart stream"),
                        }
                    }

                    // Execute the pdftotext utility
                    // pdftotext <input-pdf> <output-text-file>
                    let status = Command::new("pdftotext")
                        .arg(&input_path)
                        .arg(&output_path)
                        .status();

                    match status {
                        Ok(s) if s.success() => {
                            // Read the resulting text file
                            match std::fs::read_to_string(&output_path) {
                                Ok(content) => {
                                    return HttpResponse::Ok()
                                        .content_type("text/plain")
                                        .body(content);
                                }
                                Err(_) => return HttpResponse::InternalServerError().body("Failed to read converted text"),
                            }
                        }
                        _ => return HttpResponse::InternalServerError().body("PDF conversion failed"),
                    }
                }
            }
            Err(_) => return HttpResponse::BadRequest().body("Invalid multipart request"),
        }
    }

    HttpResponse::BadRequest().body("No file uploaded under the key 'file'")
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