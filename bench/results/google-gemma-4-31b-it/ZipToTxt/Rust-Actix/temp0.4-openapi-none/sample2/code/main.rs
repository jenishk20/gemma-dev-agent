use actix_multipart::Multipart;
use actix_web::{post, App, HttpResponse, HttpServer, Responder};
use futures_util::{StreamExt, TryStreamExt};
use std::io::{Read, Write};
use std::fs::File;
use std::path::PathBuf;
use tempdir::TempDir;

// Since the provided dependency list does not include a zip crate (like 'zip'), 
// and we are strictly forbidden from using any other packages, 
// we must implement a basic ZIP parser or use a system command.
// However, the standard way to handle ZIPs in Rust is the 'zip' crate.
// Given the strict constraint "You are not allowed to use anything besides the standard library and the following packages",
// and the fact that 'zip' is NOT in the list, I must rely on the available tools.
// Since 'nix' is provided, we can potentially interact with the OS, 
// but the most reliable way to handle ZIP files without a library is to use the system's `unzip` utility via `std::process`.

#[post("/convert")]
async fn convert_zip(mut payload: Multipart) -> impl Responder {
    let mut temp_dir = match TempDir::new() {
        Ok(dir) => dir,
        Err(_) => return HttpResponse::InternalServerError().body("Failed to create temp directory"),
    };

    let mut zip_file_path: Option<PathBuf> = None;

    // Iterate over the multipart stream
    while let Ok(Some(mut field)) = payload.try_next().await {
        if field.name() == "file" {
            let file_path = temp_dir.path().join("upload.zip");
            let mut f = match File::create(&file_path) {
                Ok(file) => file,
                Err(_) => return HttpResponse::InternalServerError().body("Failed to create upload file"),
            };

            while let Some(chunk) = field.next().await {
                match chunk {
                    Ok(data) => {
                        if let Err(_) = f.write_all(&data) {
                            return HttpResponse::InternalServerError().body("Failed to write chunk");
                        }
                    }
                    Err(_) => return HttpResponse::BadRequest().body("Error reading multipart data"),
                }
            }
            zip_file_path = Some(file_path);
        }
    }

    let zip_path = match zip_file_path {
        Some(path) => path,
        None => return HttpResponse::BadRequest().body("No file uploaded"),
    };

    // Create a directory to extract files into
    let extract_dir = temp_dir.path().join("extracted");
    if let Err(_) = std::fs::create_dir_all(&extract_dir) {
        return HttpResponse::InternalServerError().body("Failed to create extraction directory");
    }

    // Use system 'unzip' command to extract the zip file
    // This is the only way to handle zip files given the restricted dependency list
    let status = std::process::Command::new("unzip")
        .arg("-o") // overwrite files without prompting
        .arg("-d") // directory to extract into
        .arg(&extract_dir)
        .arg(&zip_path)
        .status();

    match status {
        Ok(s) if s.success() => (),
        _ => return HttpResponse::BadRequest().body("Invalid zip file or unzip utility not found"),
    }

    // Read all files in the extracted directory and concatenate their contents if they are text files
    let mut final_text = String::new();
    let walker = std::fs::read_dir(&extract_dir);
    
    if let Ok(entries) = walker {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_file() {
                // We attempt to read the file as UTF-8. If it fails, we skip it (treating it as non-text).
                if let Ok(content) = std::fs::read_to_string(&path) {
                    final_text.push_str(&content);
                    final_text.push('\n');
                }
            }
        }
    }

    HttpResponse::Ok()
        .content_type("text/plain")
        .body(final_text)
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();
    
    HttpServer::new(|| {
        App::new().service(convert_zip)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}