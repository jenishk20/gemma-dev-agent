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

    // Create a temporary directory to avoid filename collisions and cleanup
    let tmp_dir = match TempDir::new() {
        Ok(dir) => dir,
        Err(_) => return HttpResponse::InternalServerError().body("Failed to create temp directory"),
    };

    let full_path = tmp_dir.path().join(file_name);
    
    // Write the content to the file
    let mut file = match File::create(&full_path) {
        Ok(f) => f,
        Err(_) => return HttpResponse::InternalServerError().body("Failed to create file"),
    };

    if let Err(_) = file.write_all(file_content.as_bytes()) {
        return HttpResponse::InternalServerError().body("Failed to write content");
    }

    let (cmd, args) = if file_name.ends_with(".ts") {
        // TypeScript compilation: tsc <file>
        ("tsc", vec![full_path.to_str().unwrap_or("")])
    } else if file_name.ends_with(".cpp") || file_name.ends_with(".cc") {
        // C++ compilation: g++ <file> -o <out>
        let out_path = tmp_dir.path().join("out.bin");
        ("g++", vec![full_path.to_str().unwrap_or(""), "-o", out_path.to_str().unwrap_or("")])
    } else {
        return HttpResponse::BadRequest().body("Unsupported file extension. Please use .ts or .cpp");
    };

    // Execute the compiler
    let output = Command::new(cmd)
        .args(&args)
        .output();

    match output {
        Ok(out) => {
            if out.status.success() {
                HttpResponse::Ok().json(CompileResponse {
                    has_error: false,
                    compiler_error: None,
                })
            } else {
                let stderr = String::from_utf8_lossy(&out.stderr).to_string();
                let stdout = String::from_utf8_lossy(&out.stdout).to_string();
                let error_msg = if !stderr.is_empty() { stderr } else { stdout };
                
                HttpResponse::Ok().json(CompileResponse {
                    has_error: true,
                    compiler_error: Some(error_msg.trim().to_string()),
                })
            }
        }
        Err(e) => HttpResponse::InternalServerError().body(format!("Compiler execution failed: {}", e)),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();
    
    HttpServer::new(|| {
        App::new().service(compile)
    })
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}