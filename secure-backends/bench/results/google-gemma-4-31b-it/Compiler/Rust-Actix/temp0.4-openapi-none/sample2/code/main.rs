use actix_web::{post, web, App, HttpResponse, HttpServer, Responder};
use serde::{Deserialize, Serialize};
use std::fs::File;
use std::io::Write;
use std::process::Command;
use tempdir::TempDir;

#[derive(Deserialize)]
struct CompileRequest {
    #[serde(rename = "fileName")]
    file_name: String,
    #[serde(rename = "fileContent")]
    file_content: String,
}

#[derive(Serialize)]
struct CompileResponse {
    #[serde(rename = "hasError")]
    has_error: bool,
    #[serde(rename = "compilerError")]
    compiler_error: Option<String>,
}

#[post("/compile")]
async fn compile(req: web::Json<CompileRequest>) -> impl Responder {
    let file_name = &req.file_name;
    let file_content = &req.file_content;

    // Create a temporary directory to avoid file collisions and clutter
    let tmp_dir = match TempDir::new() {
        Ok(dir) => dir,
        Err(_) => return HttpResponse::InternalServerError().body("Failed to create temp directory"),
    };

    let full_path = tmp_dir.path().join(file_name);
    
    // Write the content to the file
    let mut file = match File::create(&full_path) {
        Ok(f) => f,
        Err(_) => return HttpResponse::InternalServerError().body("Failed to create source file"),
    };

    if let Err(_) = file.write_all(file_content.as_bytes()) {
        return HttpResponse::InternalServerError().body("Failed to write source file");
    }

    let extension = if file_name.ends_with(".ts") {
        Some("ts")
    } else if file_name.ends_with(".cpp") {
        Some("cpp")
    } else {
        None
    };

    let output = match extension {
        Some("ts") => {
            // Use tsc for TypeScript. 
            // --noEmit ensures we only check for errors without generating js files.
            let output = Command::new("tsc")
                .arg(full_path.to_str().unwrap())
                .arg("--noEmit")
                .arg("--esModuleInterop")
                .output();
            
            match output {
                Ok(out) => {
                    if out.status.success() {
                        None
                    } else {
                        Some(String::from_utf8_lossy(&out.stderr).to_string())
                    }
                }
                Err(_) => Some("TypeScript compiler (tsc) not found or failed to execute".to_string()),
            }
        }
        Some("cpp") => {
            // Use g++ for C++.
            let output = Command::new("g++")
                .arg(full_path.to_str().unwrap())
                .arg("-o")
                .arg(tmp_dir.path().join("out.exe").to_str().unwrap())
                .output();

            match output {
                Ok(out) => {
                    if out.status.success() {
                        None
                    } else {
                        Some(String::from_utf8_lossy(&out.stderr).to_string())
                    }
                }
                Err(_) => Some("C++ compiler (g++) not found or failed to execute".to_string()),
            }
        }
        None => return HttpResponse::BadRequest().body("Unsupported file extension. Use .ts or .cpp"),
    };

    let has_error = output.is_some();
    
    HttpResponse::Ok().json(CompileResponse {
        has_error,
        compiler_error: output,
    })
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init_from_env(env_logger::Env::new().default_filter_or("info"));

    HttpServer::new(|| {
        App::new().service(compile)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}