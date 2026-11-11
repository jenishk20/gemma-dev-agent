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
            let mut matches = false;

            // Check filename match (starts with)
            if let Some(ref filename_query) = req.search_filename {
                if let Some(file_name) = path.file_name().and_then(|s| s.to_str()) {
                    if file_name.starts_with(filename_query) {
                        matches = true;
                    }
                }
            }

            // Check content match
            if !matches {
                if let Some(ref content_query) = req.search_content {
                    if let Ok(mut file) = fs::File::open(&path) {
                        let mut buffer = String::new();
                        if file.read_to_string(&mut buffer).is_ok() {
                            if buffer.contains(content_query) {
                                matches = true;
                            }
                        }
                    }
                }
            }

            if matches {
                if let Some(path_str) = path.to_str() {
                    results.push(path_str.to_string());
                }
            }
        }
    }
}

#[post("/search")]
async fn search(req: web::Json<SearchRequest>) -> impl Responder {
    let base_data_dir = Path::new("/data");
    
    // Determine the starting directory
    let start_dir = if let Some(ref relative_path) = req.search_dir {
        base_data_dir.join(relative_path)
    } else {
        base_data_dir.to_path_buf()
    };

    if !start_dir.exists() || !start_dir.is_dir() {
        return HttpResponse::BadRequest().body("Invalid search directory");
    }

    let mut found_files = Vec::new();
    search_files_recursive(&start_dir, &req, &mut found_files);

    HttpResponse::Ok().json(SearchResponse {
        files: found_files,
    })
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();
    
    println!("Starting server on 0.0.0.0:5000...");
    HttpServer::new(|| {
        App::new().service(search)
    })
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}