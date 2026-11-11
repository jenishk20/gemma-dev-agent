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

fn search_files(
    base_dir: &Path,
    sub_dir: &Option<String>,
    filename_query: &Option<String>,
    content_query: &Option<String>,
) -> Vec<String> {
    let mut results = Vec::new();
    
    // Construct the starting directory
    let start_path = if let Some(sd) = sub_dir {
        base_dir.join(sd)
    } else {
        base_dir.to_path_buf()
    };

    if !start_path.exists() || !start_path.is_dir() {
        return results;
    }

    // Recursive walker
    let mut stack = vec![start_path];

    while let Some(current_dir) = stack.pop() {
        let entries = match fs::read_dir(current_dir) {
            Ok(e) => e,
            Err(_) => continue,
        };

        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir() {
                stack.push(path);
            } else if path.is_file() {
                let mut matches = false;

                // Check filename match
                if let Some(fn_query) = filename_query {
                    if let Some(name) = path.file_name().and_then(|n| n.to_str()) {
                        if name.contains(fn_query) {
                            matches = true;
                        }
                    }
                }

                // Check content match (only if filename didn't already match or if both are required)
                // The schema implies "contain specified content OR match filename"
                if !matches {
                    if let Some(cont_query) = content_query {
                        if let Ok(mut file) = fs::File::open(&path) {
                            let mut buffer = String::new();
                            if file.read_to_string(&mut buffer).is_ok() {
                                if buffer.contains(cont_query) {
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

    results
}

#[post("/search")]
async fn search_handler(req: web::Json<SearchRequest>) -> impl Responder {
    let base_data_path = Path::new("/data");
    
    // If /data doesn't exist on the host system, this will return empty list
    let files = search_files(
        base_data_path,
        &req.search_dir,
        &req.search_filename,
        &req.search_content,
    );

    HttpResponse::Ok().json(SearchResponse { files })
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