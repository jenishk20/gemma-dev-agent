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
    let keywords = ["unsubscribe", "remove me", "deregister me", "stop sending me", "delete me"];
    let should_unsubscribe = keywords.iter().any(|&word| content.contains(word));

    // Simple extraction of email from the "From:" header
    // Example: "From:Alex <alex@example.com>" or "From: c@sigparser.com"
    let mut email = String::from("unknown");
    for line in content.lines() {
        if line.starts_with("from:") {
            let from_part = &line[5..].trim();
            if let Some(start) = from_part.find('<') {
                if let Some(end) = from_part[start..].find('>') {
                    email = from_part[start + 1..start + end].to_string();
                }
            } else {
                // Fallback to taking the first word/string that looks like an email
                email = from_part.split_whitespace().next().unwrap_or("unknown").to_string();
            }
            break;
        }
    }

    HttpResponse::Ok().json(UnsubscribeResponse {
        email,
        unsubscribe: should_unsubscribe,
    })
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init_from_env(env_logger::Env::new().default_filter_or("info"));

    println!("Starting server at http://0.0.0.0:5000");
    HttpServer::new(|| {
        App::new().service(decide_unsubscribe)
    })
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}