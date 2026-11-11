use actix_web::{post, web, App, HttpResponse, HttpServer, Responder};
use serde::{Deserialize, Serialize};
use std::process::Command;
use std::io::{BufRead, BufReader};
use regex::Regex;

#[derive(Deserialize)]
struct MonitorRequest {
    #[serde(rename = "filter_flags")]
    filter_flags: Option<String>,
    #[serde(rename = "command_regex")]
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
    let regex = match Regex::new(&req.command_regex) {
        Ok(r) => r,
        Err(_) => return HttpResponse::BadRequest().json(ErrorResponse {
            code: 400,
            message: "Invalid regular expression".to_string(),
        }),
    };

    // Construct the ps command. 
    // Since 'command' parameter is not supported, we use flags.
    // Default flags if none provided: 'aux' is common for process listing.
    let flags = req.filter_flags.as_deref().unwrap_or("aux");
    
    // Split flags into arguments for Command::args
    let args: Vec<&str> = flags.split_whitespace().collect();

    let output = Command::new("ps")
        .args(&args)
        .output();

    match output {
        Ok(out) => {
            let stdout = String::from_utf8_lossy(&out.stdout);
            let reader = BufReader::new(stdout.as_bytes());
            let mut results = Vec::new();

            // Skip header line
            let mut lines = reader.lines();
            lines.next();

            for line in lines {
                if let Ok(l) = line {
                    if regex.is_match(&l) {
                        // ps aux output usually starts with USER, PID, %CPU, %MEM, VSZ, RSS, TTY, STAT, START, TIME, COMMAND
                        // We attempt to extract the PID (usually the second column)
                        let parts: Vec<&str> = l.split_whitespace().collect();
                        if parts.len() >= 2 {
                            if let Ok(pid) = parts[1].parse::<i32>() {
                                results.push(ProcessInfo {
                                    process_id: pid,
                                    process_string: l,
                                });
                            }
                        }
                    }
                }
            }
            HttpResponse::Ok().json(results)
        }
        Err(e) => HttpResponse::InternalServerError().json(ErrorResponse {
            code: 500,
            message: format!("Failed to execute ps command: {}", e),
        }),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();
    
    HttpServer::new(|| {
        App::new()
            .service(monitor_commands)
    })
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}