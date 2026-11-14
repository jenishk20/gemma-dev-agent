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
    if let Ok(entries) = fs::read_dir(dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir() {
                search_files(&path, content, filename, results);
            } else if path.is_file() {
                let mut matches = false;

                // Check filename match (starts with or equals)
                if let Some(ref name_query) = filename {
                    if let Some(file_name) = path.file_name().and_then(|s| s.to_str()) {
                        if file_name.starts_with(name_query) {
                            matches = true;
                        }
                    }
                }

                // Check content match
                if !matches {
                    if let Some(ref content_query) = content {
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
}

#[post("/search")]
async fn search_handler(req: web::Json<SearchRequest>) -> impl Responder {
    let base_data_dir = Path::new("/data");
    
    // Determine starting directory
    let start_dir = if let Some(ref rel_path) = req.search_dir {
        base_data_dir.join(rel_path)
    } else {
        base_data_dir.to_path_buf()
    };

    // Security check: Ensure the search directory is within /data to prevent directory traversal
    if !start_dir.starts_with(base_data_dir) {
        return HttpResponse::BadRequest().body("Invalid search directory");
    }

    let mut results = Vec::new();
    
    // If both search terms are None, we return an empty list or could return all. 
    // Based on OpenAPI, we search for files that contain content OR match filename.
    if req.search_content.is_none() && req.search_filename.is_none() {
        return HttpResponse::Ok().json(SearchResponse { files: vec![] });
    }

    search_files(&start_dir, &req.search_content, &req.search_filename, &mut results);

    HttpResponse::Ok().json(SearchResponse { files: results })
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();
    
    println!("Starting server on 0.0.0.0:5000...");
    HttpServer::new(|| {
        App::new().service(search_handler)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}