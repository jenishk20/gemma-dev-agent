use actix_multipart::Multipart;
use actix_web::{post, App, HttpResponse, HttpServer, Responder};
use futures_util::{StreamExt, TryStreamExt};
use std::io::Write;
use std::process::Command;
use tempdir::TempDir;
use uuid::Uuid;

#[post("/convert")]
async fn convert_pdf(mut payload: Multipart) -> impl Responder {
    // Iterate over the multipart stream
    while let Ok(Some(mut field)) = payload.try_next().await {
        // We only care about the "file" field as per OpenAPI spec
        if field.name() == "file" {
            // Create a temporary directory to store the uploaded PDF and the output text
            let tmp_dir = match TempDir::new() {
                Ok(dir) => dir,
                Err(_) => return HttpResponse::InternalServerError().body("Failed to create temp directory"),
            };

            let file_id = Uuid::new_v4().to_string();
            let input_path = tmp_dir.path().join(format!("{}.pdf", file_id));
            let output_path = tmp_dir.path().join(format!("{}.txt", file_id));

            // Save the uploaded bytes to a temporary file
            let mut f = match std::fs::File::create(&input_path) {
                Ok(file) => file,
                Err(_) => return HttpResponse::InternalServerError().body("Failed to create input file"),
            };

            while let Ok(Some(chunk)) = field.try_next().await {
                if let Err(_) = f.write_all(&chunk) {
                    return HttpResponse::InternalServerError().body("Failed to write file to disk");
                }
            }

            // Use the `pdftotext` utility from poppler-utils
            // Command: pdftotext <input_pdf> <output_txt>
            let status = Command::new("pdftotext")
                .arg(&input_path)
                .arg(&output_path)
                .status();

            match status {
                Ok(s) if s.success() => {
                    // Read the resulting text file
                    match std::fs::read_to_string(&output_path) {
                        Ok(text) => return HttpResponse::Ok().content_type("text/plain").body(text),
                        Err(_) => return HttpResponse::InternalServerError().body("Failed to read converted text"),
                    }
                }
                Ok(_) => return HttpResponse::InternalServerError().body("pdftotext utility failed to convert the file"),
                Err(_) => return HttpResponse::InternalServerError().body("pdftotext utility not found or failed to execute"),
            }
        }
    }

    // If no "file" field was found or processed
    HttpResponse::BadRequest().body("Missing 'file' field in multipart/form-data request")
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init_from_env(env_logger::Env::new().default_filter_or("info"));

    println!("Starting server on 0.0.0.0:5000...");
    HttpServer::new(|| {
        App::new().service(convert_pdf)
    })
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}