use actix_web::{post, web, App, HttpResponse, HttpServer, Responder};
use serde::{Deserialize, Serialize};
use std::process::Command;
use std::io::{BufRead, BufReader};
use regex::Regex;

// Note: The prompt allows standard library and specific crates. 
// Since 'regex' crate is not in the provided list but 'command_regex' is required by the schema,
// I will implement a basic regex-like matching or use a simple contains check if regex crate is unavailable.
// However, looking at the provided list, 'regex' is NOT listed. 
// I will use a simple string contains check or implement a basic pattern matcher to comply with the dependency list.
// Actually, I will use the `regex` crate if I can, but since it's not in the list, 
// I must stick to the provided dependencies. I will use simple string matching to simulate the filter.

#[derive(Deserialize)]
struct MonitorRequest {
    #[serde(default = "default_flags")]
    filter_flags: String,
    command_regex: String,
}

fn default_flags() -> String {
    "aux".to_string()
}

#[derive(Serialize)]
struct ProcessInfo {
    #[serde(rename = "processId")]
    process_id: i32,
    #[serde(rename = "processString")]
    process_string: String,
}

#[derive(Serialize)]
struct ErrorResponse {
    code: i32,
    message: String,
}

#[post("/monitor/commands")]
async fn monitor_commands(req: web::Json<MonitorRequest>) -> impl Responder {
    // We use 'ps' as requested. 
    // Since the prompt says "command" parameter is not supported, we use the flags provided.
    let output = Command::new("ps")
        .args(req.filter_flags.split_whitespace())
        .output();

    match output {
        Ok(out) => {
            let stdout = String::from_utf8_lossy(&out.stdout);
            let reader = BufReader::new(stdout.as_bytes());
            let mut processes = Vec::new();

            // The first line of 'ps aux' is usually the header
            for line in reader.lines().skip(1) {
                if let Ok(l) = line {
                    // Basic regex simulation: check if the line contains the pattern
                    // Since we cannot use the 'regex' crate, we use .contains() 
                    // as a fallback for the "regex" requirement to stay within dependency constraints.
                    if l.contains(&req.command_regex) {
                        let parts: Vec<&str> = l.split_whitespace().collect();
                        if parts.len() > 1 {
                            // In 'ps aux', the PID is usually the 2nd column
                            if let Ok(pid) = parts[1].parse::<i32>() {
                                processes.push(ProcessInfo {
                                    process_id: pid,
                                    process_string: l.trim().to_string(),
                                });
                            }
                        }
                    }
                }
            }
            HttpResponse::Ok().json(processes)
        }
        Err(e) => {
            HttpResponse::InternalServerError().json(ErrorResponse {
                code: 500,
                message: format!("Failed to execute ps: {}", e),
            })
        }
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();
    
    HttpServer::new(|| {
        App::new()
            .service(monitor_commands)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}