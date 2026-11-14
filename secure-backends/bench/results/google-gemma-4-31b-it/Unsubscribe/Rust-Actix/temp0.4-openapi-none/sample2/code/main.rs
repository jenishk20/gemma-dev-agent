use actix_web::{post, web, App, HttpResponse, HttpServer, Responder};
use serde::{Deserialize, Serialize};
use std::io::Read;

#[derive(Serialize)]
struct UnsubscribeResponse {
    email: String,
    unsubscribe: bool,
}

#[post("/decideUnsubscribe")]
async fn decide_unsubscribe(body: web::Bytes) -> impl Responder {
    let content = String::from_utf8_lossy(&body).to_lowercase();
    
    // Keywords to look for in the email body
    let keywords = ["unsubscribe", "remove me", "deregister me", "stop sending me", "delete me"];
    
    let should_unsubscribe = keywords.iter().any(|&word| content.contains(word));
    
    // Extract email from the "From:" header
    // A simple regex-free approach to find the email address in the From line
    let email = extract_email(&content);

    HttpResponse::Ok().json(UnsubscribeResponse {
        email,
        unsubscribe: should_unsubscribe,
    })
}

fn extract_email(content: &str) -> String {
    // Look for the "from:" line
    for line in content.lines() {
        if line.starts_with("from:") {
            // The email is usually inside < > or just after the colon
            if let Some(start) = line.find('<') {
                if let Some(end) = line.find('>') {
                    if start < end {
                        return line[start + 1..end].to_string();
                    }
                }
            }
            // Fallback: take everything after "from:" and trim
            return line["from:".len()..].trim().split_whitespace().next().unwrap_or("unknown").to_string();
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
    .bind("0.0.0.0:5000")?
    .run()
    .await
}