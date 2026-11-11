use actix_multipart::Multipart;
use actix_web::{post, web, App, HttpResponse, HttpServer, Responder};
use futures_util::{StreamExt, TryStreamExt};
use std::fs::File;
use std::io::Write;
use std::process::Command;
use tempdir::TempDir;
use uuid::Uuid;

#[derive(serde::Serialize)]
struct ErrorResponse {
    error: String,
}

#[post("/concatenate")]
async fn concatenate_pdfs(mut payload: Multipart) -> impl Responder {
    // Create a temporary directory to store uploaded PDFs and the result
    let temp_dir = match TempDir::new() {
        Ok(dir) => dir,
        Err(_) => return HttpResponse::InternalServerError().json(ErrorResponse {
            error: "Failed to create temporary directory".to_string(),
        }),
    };

    let mut input_files = Vec::new();

    // Iterate over the multipart stream
    while let Ok(Some(mut field)) = payload.try_next().await {
        // The OpenAPI schema specifies the field name as 'files'
        if field.name() == "files" {
            let file_id = Uuid::new_v4();
            let file_path = temp_dir.path().join(format!("{}.pdf", file_id));
            
            let mut f = match File::create(&file_path) {
                Ok(file) => file,
                Err(_) => return HttpResponse::InternalServerError().json(ErrorResponse {
                    error: "Failed to create file on disk".to_string(),
                }),
            };

            while let Ok(Some(chunk)) = field.try_next().await {
                if let Err(_) = f.write_all(&chunk) {
                    return HttpResponse::InternalServerError().json(ErrorResponse {
                        error: "Failed to write chunk to disk".to_string(),
                    });
                }
            }
            input_files.push(file_path);
        }
    }

    if input_files.is_empty() {
        return HttpResponse::BadRequest().json(ErrorResponse {
            error: "Invalid input or missing files.".to_string(),
        });
    }

    // Define output path
    let output_path = temp_dir.path().join("concatenated.pdf");

    // Prepare pdfunite command: pdfunite file1.pdf file2.pdf ... output.pdf
    let mut cmd = Command::new("pdfunite");
    cmd.args(&input_files);
    cmd.arg(&output_path);

    match cmd.status() {
        Ok(status) if status.success() => {
            // Read the resulting file and return it as application/pdf
            match std::fs::read(&output_path) {
                Ok(contents) => HttpResponse::Ok()
                    .content_type("application/pdf")
                    .body(contents),
                Err(_) => HttpResponse::InternalServerError().json(ErrorResponse {
                    error: "Failed to read the concatenated PDF".to_string(),
                }),
            }
        }
        _ => HttpResponse::InternalServerError().json(ErrorResponse {
            error: "An error occurred while processing the files.".to_string(),
        }),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();
    
    HttpServer::new(|| {
        App::new().service(concatenate_pdfs)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}