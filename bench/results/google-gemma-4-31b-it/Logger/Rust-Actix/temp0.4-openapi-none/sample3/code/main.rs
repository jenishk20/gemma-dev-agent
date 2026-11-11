use actix_web::{get, post, web, App, HttpResponse, HttpServer, Responder};
use serde::{Deserialize, Serialize};
use std::fs::{OpenOptions, read_to_string};
use std::io::Write;
use std::sync::Mutex;

#[derive(Deserialize, Serialize)]
struct LogRequest {
    message: String,
}

struct AppState {
    file_path: Mutex<String>,
}

#[post("/log")]
async fn log_message(data: web::Data<AppState>, payload: web::Json<LogRequest>) -> impl Responder {
    let path = data.file_path.lock().unwrap();
    
    // Open file in append mode, create if it doesn't exist
    let result = OpenOptions::new()
        .create(true)
        .append(true)
        .open(path.as_str());

    match result {
        Ok(mut file) => {
            if let Err(e) = writeln!(file, "{}", payload.message) {
                return HttpResponse::InternalServerError().body(format!("Error writing to file: {}", e));
            }
            HttpResponse::Ok().finish()
        }
        Err(e) => HttpResponse::InternalServerError().body(format!("Error opening file: {}", e)),
    }
}

#[get("/logs")]
async fn get_logs(data: web::Data<AppState>) -> impl Responder {
    let path = data.file_path.lock().unwrap();
    
    match read_to_string(path.as_str()) {
        Ok(content) => HttpResponse::Ok().content_type("text/plain").body(content),
        Err(_) => HttpResponse::Ok().content_type("text/plain").body(""), // Return empty if file doesn't exist yet
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let app_state = web::Data::new(AppState {
        file_path: Mutex::new("logs.txt".to_string()),
    });

    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .service(log_message)
            .service(get_logs)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}