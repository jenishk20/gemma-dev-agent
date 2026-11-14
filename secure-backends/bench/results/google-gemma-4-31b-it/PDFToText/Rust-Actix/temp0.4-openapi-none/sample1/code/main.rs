use actix_multipart::Multipart;
use actix_web::{post, App, HttpResponse, HttpServer, Responder};
use futures_util::{StreamExt, TryStreamExt};
use std::fs::File;
use std::io::Write;
use std::process::Command;
use tempdir::TempDir;
use uuid::Uuid;

#[post("/convert")]
async fn convert_pdf_to_text(mut payload: Multipart) -> impl Responder {
    let mut file_content = Vec::new();
    let mut file_received = false;

    // Iterate over the multipart stream
    while let Ok(Some(mut field)) = payload.try_next().await {
        // We only care about the field named "file"
        if field.name() == "file" {
            file_received = true;
            while let Some(chunk) = field.next().await {
                match chunk {
                    Ok(data) => file_content.extend_from_slice(&data),
                    Err(_) => return HttpResponse::BadRequest().body("Error reading file stream"),
                }
            }
        }
    }

    if !file_received || file_content.is_empty() {
        return HttpResponse::BadRequest().body("Missing file in request");
    }

    // Use a temporary directory to store the PDF and the resulting text file
    let temp_dir = match TempDir::new() {
        Ok(dir) => dir,
        Err(_) => return HttpResponse::InternalServerError().body("Failed to create temp directory"),
    };

    let request_id = Uuid::new_v4().to_string();
    let pdf_path = temp_dir.path().join(format!("{}.pdf", request_id));
    let txt_path = temp_dir.path().join(format!("{}.txt", request_id));

    // Write the uploaded bytes to a temporary PDF file
    let mut f = match File::create(&pdf_path) {
        Ok(file) => file,
        Err(_) => return HttpResponse::InternalServerError().body("Failed to create temporary file"),
    };

    if let Err(_) = f.write_all(&file_content) {
        return HttpResponse::InternalServerError().body("Failed to write PDF content");
    }

    // Execute the pdftotext utility
    // pdftotext <input-pdf> <output-txt>
    let output = Command::new("pdftotext")
        .arg(&pdf_path)
        .arg(&txt_path)
        .output();

    match output {
        Ok(out) if out.status.success() => {
            // Read the generated text file
            match std::fs::read_to_string(&txt_path) {
                Ok(text) => HttpResponse::Ok().content_type("text/plain").body(text),
                Err(_) => HttpResponse::InternalServerError().body("Failed to read converted text"),
            }
        }
        Ok(_) => {
            HttpResponse::InternalServerError().body("pdftotext utility failed to process the file")
        }
        Err(_) => {
            HttpResponse::InternalServerError().body("pdftotext utility not found or failed to execute")
        }
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