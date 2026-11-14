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
    let content = String::from_utf8_lossy(&body).to_string();
    
    // Extract email from "From: Name <email@domain.com>" or "From: email@domain.com"
    let email = extract_email(&content);
    
    // Check for unsubscribe keywords
    let keywords = ["unsubscribe", "remove me", "deregister me", "stop sending me", "delete me"];
    let lower_content = content.to_lowercase();
    let should_unsubscribe = keywords.iter().any(|&kw| lower_content.contains(kw));

    HttpResponse::Ok().json(UnsubscribeResponse {
        email,
        unsubscribe: should_unsubscribe,
    })
}

fn extract_email(text: &str) -> String {
    for line in text.lines() {
        if line.to_lowercase().starts_with("from:") {
            let line_content = &line[5..].trim();
            
            // Try to find email inside angle brackets < >
            if let Some(start) = line_content.find('<') {
                if let Some(end) = line_content.find('>') {
                    return line_content[start + 1..end].to_string();
                }
            }
            
            // Fallback: return the trimmed line if no brackets found
            return line_content.split_whitespace().next().unwrap_or("").to_string();
        }
    }
    "unknown".to_string()
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