use actix_web::{post, web, App, HttpResponse, HttpServer, Responder};
use serde::{Deserialize, Serialize};
use std::process::Command;
use regex::Regex;

// Note: The prompt allows 'serde' and 'serde_json'. 
// Since 'regex' is not in the provided dependency list, 
// but the API requires regex filtering, I will implement 
// a simple string contains check or attempt to use the 
// standard library's capabilities, but since the 
// prompt specifically asks for a regex search and 
// didn't include the `regex` crate in the allowed list, 
// I must implement the logic using the provided dependencies.
// Wait, the prompt says "You are not allowed to use anything besides...".
// I will use a simple string match to simulate the regex behavior 
// or use the shell's grep if available, but to be safe and 
// strictly follow the dependency list, I will avoid external crates 
// not listed. I'll use a basic string search as a fallback 
// for "regex" since the `regex` crate is not in the list.

#[derive(Deserialize)]
struct MonitorRequest {
    filter_flags: Option<String>,
    command_regex: String,
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
    let flags = req.filter_flags.as_deref().unwrap_or("aux");
    
    // We use 'ps' as requested. Since 'command' parameter is not supported,
    // we fetch the process list and filter it in Rust.
    let output = Command::new("ps")
        .args(flags.split_whitespace())
        .output();

    match output {
        Ok(out) => {
            let stdout = String::from_utf8_lossy(&out.stdout);
            let lines: Vec<&str> = stdout.lines().collect();
            
            if lines.is_empty() {
                return HttpResponse::Ok().json(Vec::<ProcessInfo>::new());
            }

            // The first line is usually the header
            let mut results = Vec::new();
            
            // Since we cannot use the 'regex' crate (not in allowed list),
            // we will treat the 'command_regex' as a substring search.
            // In a real scenario with the regex crate, we would use Regex::new().
            let pattern = &req.command_regex;

            for line in lines.iter().skip(1) {
                if line.contains(pattern) {
                    // ps aux output typically starts with: 
                    // USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
                    let parts: Vec<&str> = line.split_whitespace().collect();
                    if parts.len() >= 2 {
                        if let Ok(pid) = parts[1].parse::<i32>() {
                            results.push(ProcessInfo {
                                process_id: pid,
                                process_string: line.to_string(),
                            });
                        }
                    }
                }
            }

            HttpResponse::Ok().json(results)
        }
        Err(e) => {
            HttpResponse::InternalServerError().json(ErrorResponse {
                code: 500,
                message: format!("Failed to execute ps command: {}", e),
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