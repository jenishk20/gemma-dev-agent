use actix_multipart::Multipart;
use actix_web::{post, web, App, HttpResponse, HttpServer, Responder};
use futures_util::{StreamExt, TryStreamExt};
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
        Err(_) => return HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to create temporary directory"})),
    };

    let mut pdf_paths = Vec::new();

    // Process the multipart stream
    while let Ok(Some(mut field)) = payload.try_next().await {
        // The OpenAPI schema specifies the field name as 'files'
        if field.name() == "files" {
            let file_id = Uuid::new_v4();
            let file_path = temp_dir.path().join(format!("{}.pdf", file_id));
            
            let mut f = match File::create(&file_path) {
                Ok(file) => file,
                Err(_) => return HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to create file on disk"})),
            };

            while let Ok(Some(chunk)) = field.try_next().await {
                if let Err(_) = f.write_all(&chunk) {
                    return HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to write chunk to disk"}));
                }
            }
            pdf_paths.push(file_path);
        }
    }

    if pdf_paths.is_empty() {
        return HttpResponse::BadRequest().json(serde_json::json!({"error": "Invalid input or missing files."}));
    }

    // Define output path
    let output_filename = format!("{}.pdf", Uuid::new_v4());
    let output_path = temp_dir.path().join(&output_filename);

    // Build the pdfunite command: pdfunite file1.pdf file2.pdf ... output.pdf
    let mut cmd = Command::new("pdfunite");
    for path in &pdf_paths {
        cmd.arg(path);
    }
    cmd.arg(&output_path);

    // Execute the command
    match cmd.status() {
        Ok(status) if status.success() => {
            // Read the resulting PDF file to return it
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
    
    println!("Starting server on 0.0.0.0:5000...");
    HttpServer::new(|| {
        App::new().service(concatenate_pdfs)
    })
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}