use actix_multipart::Multipart;
use actix_web::{post, App, HttpResponse, HttpServer, Responder};
use futures_util::{StreamExt, TryStreamExt};
use std::fs::File;
use std::io::Write;
use std::process::Command;
use tempdir::TempDir;
use uuid::Uuid;

#[post("/concatenate")]
async fn concatenate_pdfs(mut payload: Multipart) -> impl Responder {
    // Create a temporary directory to store uploaded PDFs and the result
    let tmp_dir = match TempDir::new() {
        Ok(dir) => dir,
        Err(_) => return HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to create temp directory"})),
    };
    let tmp_path = tmp_dir.path();

    let mut uploaded_files = Vec::new();

    // Iterate over the multipart stream
    while let Ok(Some(mut field)) = payload.try_next().await {
        // We only care about fields named "files" as per the OpenAPI spec
        if field.name() == "files" {
            let file_id = Uuid::new_v4();
            let file_path = tmp_path.join(format!("{}.pdf", file_id));
            
            let mut f = match File::create(&file_path) {
                Ok(file) => file,
                Err(_) => return HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to create file on disk"})),
            };

            while let Ok(Some(chunk)) = field.try_next().await {
                if let Err(_) = f.write_all(&chunk) {
                    return HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to write file chunk"}));
                }
            }
            uploaded_files.push(file_path);
        }
    }

    if uploaded_files.is_empty() {
        return HttpResponse::BadRequest().json(serde_json::json!({"error": "Invalid input or missing files."}));
    }

    // Define output path
    let output_path = tmp_path.join("concatenated.pdf");

    // Build the pdfunite command: pdfunite file1.pdf file2.pdf ... output.pdf
    let mut cmd = Command::new("pdfunite");
    for path in &uploaded_files {
        cmd.arg(path);
    }
    cmd.arg(&output_path);

    // Execute the command
    match cmd.status() {
        Ok(status) if status.success() => {
            // Read the resulting PDF file
            match std::fs::read(&output_path) {
                Ok(contents) => {
                    HttpResponse::Ok()
                        .content_type("application/pdf")
                        .body(contents)
                }
                Err(_) => HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to read concatenated PDF"})),
            }
        }
        _ => {
            HttpResponse::InternalServerError().json(serde_json::json!({"error": "An error occurred while processing the files."}))
        }
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();
    
    println!("Starting server on 0.0.0.0:5000...");
    
    HttpServer::new(|| {
        App::new()
            .service(concatenate_pdfs)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}