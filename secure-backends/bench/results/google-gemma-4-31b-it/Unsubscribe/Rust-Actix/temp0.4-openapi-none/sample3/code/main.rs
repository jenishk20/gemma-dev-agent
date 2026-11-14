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
    
    // Keywords to trigger unsubscribe
    let keywords = vec![
        "unsubscribe",
        "remove me",
        "deregister me",
        "stop sending me",
        "delete me",
    ];

    // Determine if any keyword is present in the email body
    let should_unsubscribe = keywords.iter().any(|&k| content.contains(k));

    // Extract email address from "From: ..." header
    // A simple regex-like approach to find the email inside angle brackets < > 
    // or immediately following "From: "
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
            // Try to find email inside < >
            if let Some(start) = line.find('<') {
                if let Some(end) = line.find('>') {
                    if start < end {
                        return line[start + 1..end].to_string();
                    }
                }
            }
            // Fallback: take everything after "from:" and trim
            return line["from:".len()..].trim().to_string();
        }
    }
    "unknown@example.com".to_string()
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();
    
    println!("Starting server on 0.0.0.0:5000");
    
    HttpServer::new(|| {
        App::new()
            .service(decide_unsubscribe)
    })
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}