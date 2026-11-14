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
    let content = &req.file_content;

    // Create a temporary directory to hold the source file
    let tmp_dir = match TempDir::new() {
        Ok(dir) => dir,
        Err(_) => return HttpResponse::InternalServerError().body("Failed to create temp dir"),
    };

    let file_path = tmp_dir.path().join(file_name);
    
    // Write content to file
    if let Err(e) = File::create(&file_path).and_then(|mut f| f.write_all(content.as_bytes())) {
        return HttpResponse::InternalServerError().body(format!("Failed to write file: {}", e));
    }

    let (cmd, args) = if file_name.ends_with(".ts") {
        // TypeScript compilation using tsc
        // --noEmit is used because we only care about the errors, not the JS output
        ("tsc", vec![file_path.to_str().unwrap_or(""), "--noEmit", "--esModuleInterop"])
    } else if file_name.ends_with(".cpp") {
        // C++ compilation using g++
        ("g++", vec![file_path.to_str().unwrap_or(""), "-o", "out.bin"])
    } else {
        return HttpResponse::BadRequest().body("Unsupported file extension. Please use .ts or .cpp");
    };

    let output = Command::new(cmd)
        .args(&args)
        .current_dir(tmp_dir.path())
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
    env_logger::init_from_env(env_logger::Env::new().default_filter_or("info"));

    println!("Starting server on 0.0.0.0:5000...");
    HttpServer::new(|| {
        App::new().service(compile)
    })
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}