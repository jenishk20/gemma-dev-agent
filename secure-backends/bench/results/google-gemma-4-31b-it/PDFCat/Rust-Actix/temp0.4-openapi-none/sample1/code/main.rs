use actix_multipart::Multipart;
use actix_web::{post, App, HttpResponse, HttpServer, Responder};
use futures_util::StreamExt;
use std::fs::File;
use std::io::Write;
use std::process::Command;
use tempdir::TempDir;
use uuid::Uuid;

#[post("/concatenate")]
async fn concatenate_pdfs(mut payload: Multipart) -> impl Responder {
    // Create a temporary directory to store uploaded PDF fragments
    let temp_dir = match TempDir::new() {
        Ok(dir) => dir,
        Err(_) => return HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to create temp directory"})),
    };

    let mut pdf_paths = Vec::new();

    // Iterate over the multipart stream
    while let Some(item) = payload.next().await {
        match item {
            Ok(mut field) => {
                // We only care about fields named "files" as per OpenAPI spec
                if field.name() == "files" {
                    let file_id = Uuid::new_v4();
                    let file_path = temp_dir.path().join(format!("{}.pdf", file_id));
                    
                    let mut f = match File::create(&file_path) {
                        Ok(file) => file,
                        Err(_) => return HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to create file on disk"})),
                    };

                    while let Some(chunk) = field.next().await {
                        match chunk {
                            Ok(data) => {
                                if let Err(_) = f.write_all(&data) {
                                    return HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to write chunk to disk"}));
                                }
                            }
                            Err(_) => return HttpResponse::BadRequest().json(serde_json::json!({"error": "Error reading multipart data"})),
                        }
                    }
                    pdf_paths.push(file_path);
                }
            }
            Err(_) => return HttpResponse::BadRequest().json(serde_json::json!({"error": "Invalid multipart request"})),
        }
    }

    if pdf_paths.is_empty() {
        return HttpResponse::BadRequest().json(serde_json::json!({"error": "Invalid input or missing files."}));
    }

    // Define output path
    let output_filename = format!("{}.pdf", Uuid::new_v4());
    let output_path = temp_dir.path().join(&output_filename);

    // Construct the pdfunite command: pdfunite file1.pdf file2.pdf ... output.pdf
    let mut cmd = Command::new("pdfunite");
    for path in &pdf_paths {
        cmd.arg(path);
    }
    cmd.arg(&output_path);

    // Execute the command
    match cmd.status() {
        Ok(status) if status.success() => {
            // Read the resulting PDF back into memory to return it
            match std::fs::read(&output_path) {
                Ok(contents) => HttpResponse::Ok()
                    .content_type("application/pdf")
                    .body(contents),
                Err(_) => HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to read concatenated PDF"})),
            }
        }
        _ => HttpResponse::InternalServerError().json(serde_json::json!({"error": "An error occurred while processing the files."})),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();
    
    println!("Starting PDF Concatenation Service on 0.0.0.0:5000");
    
    HttpServer::new(|| {
        App::new().service(concatenate_pdfs)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}