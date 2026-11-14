use actix_multipart::Multipart;
use actix_web::{post, web, App, HttpResponse, HttpServer, Responder};
use futures_util::{StreamExt, TryStreamExt};
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

    let mut input_files = Vec::new();

    // Iterate over the multipart stream
    while let Ok(Some(mut field)) = payload.try_next().await {
        let content_type = field.content_type();
        let content_disposition = field.content_disposition();

        // We only care about fields named "files"
        if let Some(cd) = content_disposition {
            if cd.get_parameter("name") == Some("files") {
                let file_id = Uuid::new_v4().to_string();
                let file_path = temp_dir.path().join(format!("{}.pdf", file_id));
                
                let mut f = match std::fs::File::create(&file_path) {
                    Ok(file) => file,
                    Err(_) => return HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to create file on disk"})),
                };

                while let Some(chunk) = field.next().await {
                    match chunk {
                        Ok(data) => {
                            if let Err(_) = f.write_all(&data) {
                                return HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to write file data"}));
                            }
                        }
                        Err(_) => return HttpResponse::BadRequest().json(serde_json::json!({"error": "Error reading multipart stream"})),
                    }
                }
                input_files.push(file_path);
            }
        }
    }

    if input_files.is_empty() {
        return HttpResponse::BadRequest().json(serde_json::json!({"error": "Invalid input or missing files."}));
    }

    // Define the output path
    let output_path = temp_dir.path().join("concatenated.pdf");

    // Build the pdfunite command: pdfunite file1.pdf file2.pdf ... output.pdf
    let mut cmd = Command::new("pdfunite");
    for path in &input_files {
        cmd.arg(path);
    }
    cmd.arg(&output_path);

    // Execute the command
    match cmd.status() {
        Ok(status) if status.success() => {
            // Read the resulting PDF file and return it
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
        App::new()
            .service(concatenate_pdfs)
    })
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}