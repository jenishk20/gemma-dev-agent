use actix_web::{post, web, App, HttpResponse, HttpServer, Responder};
use serde::{Deserialize, Serialize};
use std::io::Read;

#[derive(Serialize, Deserialize)]
struct UnsubscribeResponse {
    email: String,
    unsubscribe: bool,
}

#[post("/decideUnsubscribe")]
async fn decide_unsubscribe(body: web::Bytes) -> impl Responder {
    let content = String::from_utf8_lossy(&body).to_lowercase();
    
    // Keywords to look for in the email body
    let keywords = [
        "unsubscribe",
        "remove me",
        "deregister me",
        "stop sending me",
        "delete me",
    ];

    // Check if any keyword is present
    let should_unsubscribe = keywords.iter().any(|&k| content.contains(k));

    // Extract email address from the "From:" header
    // A simple regex-free approach to find the email inside < > or after "From: "
    let email = extract_email(&content);

    HttpResponse::Ok().json(UnsubscribeResponse {
        email,
        unsubscribe: should_unsubscribe,
    })
}

fn extract_email(content: &str) -> String {
    // Look for the "from:" line
    if let Some(from_line_start) = content.find("from:") {
        let from_line_end = content[from_line_start..]
            .find('\n')
            .map(|end| from_line_start + end)
            .unwrap_or(content.len());
        
        let from_line = &content[from_line_start..from_line_end];
        
        // Try to find email inside angle brackets <email@domain.com>
        if let Some(start) = from_line.find('<') {
            if let Some(end) = from_line.find('>') {
                if start < end {
                    return from_line[start + 1..end].to_string();
                }
            }
        }
        
        // Fallback: try to find something that looks like an email (contains @)
        for word in from_line.split_whitespace() {
            if word.contains('@') {
                return word.trim_matches(|c: char| !c.is_alphanumeric() && c != '@' && c != '.').to_string();
            }
        }
    }
    "unknown@example.com".to_string()
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();

    HttpServer::new(|| {
        App::new().service(decide_unsubscribe)
    })
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}