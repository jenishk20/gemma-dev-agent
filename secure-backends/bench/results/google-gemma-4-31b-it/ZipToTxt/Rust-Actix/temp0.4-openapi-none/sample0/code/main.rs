use actix_multipart::Multipart;
use actix_web::{post, App, HttpResponse, HttpServer, Responder};
use futures_util::{StreamExt, TryStreamExt};
use std::io::{Read, Write};
use std::fs::File;
use std::path::Path;
use tempdir::TempDir;

// Note: Since the provided dependency list does not include a zip library (like `zip` or `zip-temp`),
// and I am strictly forbidden from using packages not in the list, 
// I must implement the logic using the provided tools.
// However, the provided list lacks a ZIP decompression library. 
// In a real scenario, `zip` crate is required. 
// Given the constraint "You are not allowed to use anything besides the standard library and the following packages",
// and the fact that the standard library does not handle ZIP files, 
// I will implement the multipart handling and the logic structure.
// Since I cannot add `zip = "..."` to the dependencies, I will simulate the extraction 
// or assume the environment allows for a system call if necessary, but for a robust 
// implementation, a library is needed. 
// Wait, looking at the list again, there is no zip crate. 
// I will use `std::process::Command` to call `unzip` which is standard on most Unix systems 
// to adhere to the "no extra crates" rule while still fulfilling the functional requirement.

#[post("/convert")]
async fn convert_zip(mut payload: Multipart) -> impl Responder {
    let temp_dir = TempDir::new().expect("Failed to create temp dir");
    let upload_path = temp_dir.path().join("upload.zip");
    let extract_path = temp_dir.path().join("extracted");
    
    std::fs::create_dir_all(&extract_path).expect("Failed to create extract dir");

    // 1. Save the uploaded multipart file to disk
    while let Ok(Some(mut field)) = payload.try_next().await {
        if field.name() == "file" {
            let mut f = File::create(&upload_path).expect("Failed to create file");
            while let Some(chunk) = field.next().await {
                let data = chunk.expect("Error reading chunk");
                f.write_all(&data).expect("Error writing chunk");
            }
        }
    }

    if !upload_path.exists() {
        return HttpResponse::BadRequest().body("No file uploaded");
    }

    // 2. Unzip the file using system command 'unzip' (since no zip crate is provided in the list)
    let status = std::process::Command::new("unzip")
        .arg("-o") // overwrite
        .arg("-d")
        .arg(&extract_path)
        .arg(&upload_path)
        .status();

    match status {
        Ok(s) if s.success() => {
            // 3. Iterate through extracted files and concatenate text
            let mut result_text = String::new();
            let paths = std::fs::read_dir(&extract_path).expect("Failed to read extracted dir");

            for path in paths {
                if let Ok(entry) = path {
                    let path = entry.path();
                    if path.is_file() {
                        // Attempt to read as text
                        if let Ok(content) = std::fs::read_to_string(&path) {
                            result_text.push_str(&content);
                            result_text.push('\n');
                        }
                    } else if path.is_dir() {
                        // Recursively handle directories if necessary
                        let sub_paths = std::fs::read_dir(&path).expect("Failed to read sub dir");
                        for sub_entry in sub_paths {
                            if let Ok(se) = sub_entry {
                                if let Ok(content) = std::fs::read_to_string(&se.path()) {
                                    result_text.push_str(&content);
                                    result_text.push('\n');
                                }
                            }
                        }
                    }
                }
            }
            HttpResponse::Ok().content_type("text/plain").body(result_text)
        }
        _ => HttpResponse::BadRequest().body("Invalid zip file or unzip utility not found on system"),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();
    
    println!("Starting server at http://0.0.0.0:5000");
    HttpServer::new(|| {
        App::new().service(convert_zip)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}