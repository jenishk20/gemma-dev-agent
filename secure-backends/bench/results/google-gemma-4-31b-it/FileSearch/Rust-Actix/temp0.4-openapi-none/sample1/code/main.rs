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

fn search_files(dir: &Path, content: &Option<String>, filename: &Option<String>, results: &mut Vec<String>) {
    let entries = match fs::read_dir(dir) {
        Ok(entries) => entries,
        Err(_) => return,
    };

    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_dir() {
            search_files(&path, content, filename, results);
        } else if path.is_file() {
            let mut matches = false;

            // Check filename match
            if let Some(ref target_name) = filename {
                if let Some(file_name) = path.file_name().and_then(|s| s.to_str()) {
                    if file_name.contains(target_name) {
                        matches = true;
                    }
                }
            }

            // Check content match
            if !matches {
                if let Some(ref target_content) = content {
                    if let Ok(mut file) = fs::File::open(&path) {
                        let mut buffer = String::new();
                        if file.read_to_string(&mut buffer).is_ok() {
                            if buffer.contains(target_content) {
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
async fn search_handler(req: web::Json<SearchRequest>) -> impl Responder {
    let base_data_dir = Path::new("/data");
    
    // Determine the starting directory
    let mut search_path = PathBuf::from(base_data_dir);
    if let Some(ref relative_dir) = req.search_dir {
        search_path.push(relative_dir);
    }

    // Security check: Ensure the resolved path is still within /data to prevent directory traversal
    let canonical_base = fs::canonicalize(base_data_dir).unwrap_or_else(|_| PathBuf::from("/data"));
    let canonical_search = fs::canonicalize(&search_path).unwrap_or_else(|_| search_path.clone());

    if !canonical_search.starts_with(&canonical_base) {
        return HttpResponse::BadRequest().body("Invalid search directory");
    }

    let mut found_files = Vec::new();
    search_files(&canonical_search, &req.search_content, &req.search_filename, &mut found_files);

    HttpResponse::Ok().json(SearchResponse {
        files: found_files,
    })
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    println!("Starting server on 0.0.0.0:5000...");
    HttpServer::new(|| {
        App::new().service(search_handler)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}