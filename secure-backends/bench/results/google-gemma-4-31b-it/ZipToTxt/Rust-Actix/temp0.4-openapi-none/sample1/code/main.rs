use actix_multipart::Multipart;
use actix_web::{post, App, HttpResponse, HttpServer, Responder};
use futures_util::StreamExt;
use std::fs::File;
use std::io::{Read, Write};
use std::path::Path;
use tempdir::TempDir;

// Since the provided dependency list does not include a zip library (like `zip` or `zip-rs`),
// and the prompt strictly forbids using anything besides the provided list,
// we must implement the logic using the available tools.
// However, standard library does not provide zip decompression.
// Given the constraints, I will implement the handler using a temporary directory 
// and a simulated decompression logic or a shell call if available, 
// but since I cannot add dependencies, I must rely on the provided crates.
// Wait, the provided list is missing a zip library. 
// In a real scenario, I would need `zip` crate. 
// Since I must follow the prompt exactly and cannot add crates, 
// I will implement the multipart handling and the logic to process the file.
// To make this functional without a zip crate, I will use a system call to `unzip` 
// which is standard on most Unix-like environments where Actix is deployed.

#[post("/convert")]
async fn convert_zip_to_txt(mut payload: Multipart) -> impl Responder {
    let mut result_text = String::new();
    let mut file_saved = false;

    // Create a temporary directory to extract files
    let temp_dir = match TempDir::new() {
        Ok(dir) => dir,
        Err(_) => return HttpResponse::InternalServerError().body("Failed to create temp dir"),
    };

    while let Some(item) = payload.next().await {
        let mut field = match item {
            Ok(f) => f,
            Err(_) => return HttpResponse::BadRequest().body("Invalid multipart request"),
        };

        // We only care about the 'file' field
        if field.name() == "file" {
            let zip_path = temp_dir.path().join("input.zip");
            let mut f = File::create(&zip_path).unwrap();

            while let Some(chunk) = field.next().await {
                let data = match chunk {
                    Ok(d) => d,
                    Err(_) => return HttpResponse::BadRequest().body("Error reading file chunk"),
                };
                f.write_all(&data).unwrap();
            }
            file_saved = true;
        }
    }

    if !file_saved {
        return HttpResponse::BadRequest().body("No file uploaded");
    }

    // Use system 'unzip' command to extract files into the temp directory
    // This is the only way to handle zip files given the restricted dependency list
    let extract_status = std::process::Command::new("unzip")
        .arg("-o") // overwrite files without prompting
        .arg("-d")
        .arg(temp_dir.path())
        .arg(temp_dir.path().join("input.zip"))
        .status();

    match extract_status {
        Ok(status) if status.success() => {
            // Iterate through extracted files and collect text content
            if let Ok(entries) = std::fs::read_dir(temp_dir.path()) {
                for entry in entries.flatten() {
                    let path = entry.path();
                    if path.is_file() && path != temp_dir.path().join("input.zip") {
                        // Check if it's a text file (simple check by extension or attempting to read)
                        if let Ok(content) = std::fs::read_to_string(&path) {
                            result_text.push_str(&content);
                            result_text.push('\n');
                        }
                    }
                }
            }
            HttpResponse::Ok().content_type("text/plain").body(result_text)
        }
        _ => HttpResponse::BadRequest().body("Invalid zip file or unzip utility not found"),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();
    
    HttpServer::new(|| {
        App::new().service(convert_zip_to_txt)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}