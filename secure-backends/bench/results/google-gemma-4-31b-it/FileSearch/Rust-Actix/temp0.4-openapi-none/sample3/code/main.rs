use actix_web::{post, web, App, HttpResponse, HttpServer, Responder};
use serde::{Deserialize, Serialize};
use std::fs;
use std::io::{Read};
use std::path::{Path, PathBuf};

#[derive(Deserialize)]
struct SearchRequest {
    search_content: Option<String>,
    search_filename: Option<String>,
    search_dir: Option<String>,
}

#[derive(Serialize)]
struct SearchResponse {
    files: Vec<String>,
}

fn search_files_recursive(dir: &Path, req: &SearchRequest, results: &mut Vec<String>) {
    let entries = match fs::read_dir(dir) {
        Ok(entries) => entries,
        Err(_) => return,
    };

    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_dir() {
            search_files_recursive(&path, req, results);
        } else if path.is_file() {
            let filename = path.file_name().and_then(|n| n.to_str()).unwrap_or("");
            let path_str = path.to_string_lossy().to_string();

            // Check filename match (starts with)
            let name_match = if let Some(ref target_name) = req.search_filename {
                filename.starts_with(target_name)
            } else {
                true
            };

            // Check content match
            let content_match = if let Some(ref target_content) = req.search_content {
                if let Ok(mut file) = fs::File::open(&path) {
                    let mut buffer = String::new();
                    // Read file content. Using a simple read_to_string. 
                    // In a production env, we'd handle binary files or large files more carefully.
                    if file.read_to_string(&mut buffer).is_ok() {
                        buffer.contains(target_content)
                    } else {
                        false
                    }
                } else {
                    false
                }
            } else {
                true
            };

            if name_match && content_match {
                results.push(path_str);
            }
        }
    }
}

#[post("/search")]
async fn search(req: web::Json<SearchRequest>) -> impl Responder {
    let base_data_dir = Path::new("/data");
    
    // Determine the starting directory
    let mut search_path = PathBuf::from(base_data_dir);
    if let Some(ref relative_dir) = req.search_dir {
        search_path.push(relative_dir);
    }

    // Security check: Ensure the search path is still within /data to prevent directory traversal
    if !search_path.starts_with(base_data_dir) {
        return HttpResponse::BadRequest().body("Invalid search directory");
    }

    if !search_path.exists() || !search_path.is_dir() {
        return HttpResponse::BadRequest().body("Search directory does not exist");
    }

    let mut found_files = Vec::new();
    search_files_recursive(&search_path, &req, &mut found_files);

    HttpResponse::Ok().json(SearchResponse {
        files: found_files,
    })
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();
    
    HttpServer::new(|| {
        App::new().service(search)
    })
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}