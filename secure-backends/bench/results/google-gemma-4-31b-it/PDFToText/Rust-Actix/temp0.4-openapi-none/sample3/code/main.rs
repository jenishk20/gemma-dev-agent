use actix_multipart::Multipart;
use actix_web::{post, App, HttpResponse, HttpServer, Responder};
use futures_util::StreamExt;
use std::fs::File;
use std::io::Write;
use std::process::Command;
use tempdir::TempDir;
use uuid::Uuid;

#[post("/convert")]
async fn convert_pdf_to_text(mut payload: Multipart) -> impl Responder {
    // We use a temporary directory to handle the uploaded file and the output text file
    let tmp_dir = match TempDir::new() {
        Ok(dir) => dir,
        Err(_) => return HttpResponse::InternalServerError().body("Failed to create temp directory"),
    };

    let mut file_path = String::new();

    // Process the multipart stream
    while let Some(item) = payload.next().await {
        let mut field = match item {
            Ok(f) => f,
            Err(_) => return HttpResponse::BadRequest().body("Error processing multipart data"),
        };

        // We only care about the 'file' field as per OpenAPI spec
        if field.name() == "file" {
            let file_id = Uuid::new_v4().to_string();
            let path = format!("{}/{}.pdf", tmp_dir.path().to_str().unwrap(), file_id);
            
            let mut f = match File::create(&path) {
                Ok(file) => file,
                Err(_) => return HttpResponse::InternalServerError().body("Failed to create temporary file"),
            };

            while let Some(chunk) = field.next().await {
                let data = match chunk {
                    Ok(d) => d,
                    Err(_) => return HttpResponse::BadRequest().body("Error reading file chunk"),
                };
                if let Err(_) = f.write_all(&data) {
                    return HttpResponse::InternalServerError().body("Failed to write file to disk");
                }
            }
            file_path = path;
            break; // Only process the first 'file' field found
        }
    }

    if file_path.is_empty() {
        return HttpResponse::BadRequest().body("Missing 'file' field in request");
    }

    // Define output path for pdftotext
    let output_path = format!("{}.txt", file_path);

    // Execute pdftotext utility
    // Command: pdftotext <input.pdf> <output.txt>
    let status = Command::new("pdftotext")
        .arg(&file_path)
        .arg(&output_path)
        .status();

    match status {
        Ok(s) if s.success() => {
            // Read the resulting text file
            match std::fs::read_to_string(&output_path) {
                Ok(content) => HttpResponse::Ok().content_type("text/plain").body(content),
                Err(_) => HttpResponse::InternalServerError().body("Failed to read converted text"),
            }
        }
        Ok(_) => HttpResponse::InternalServerError().body("pdftotext utility failed to convert the file"),
        Err(_) => HttpResponse::InternalServerError().body("pdftotext utility not found or failed to execute"),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init_from_env(env_logger::Env::new().default_filter_or("info"));

    println!("Starting server on 0.0.0.0:5000...");
    HttpServer::new(|| {
        App::new().service(convert_pdf_to_text)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}