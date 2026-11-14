use actix_web::{post, get, web, App, HttpResponse, HttpServer, Responder};
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
async fn log_message(data: web::Data<AppState>, req: web::Json<LogRequest>) -> impl Responder {
    let path = data.file_path.lock().unwrap();
    
    // Open file in append mode, create if it doesn't exist
    let result = OpenOptions::new()
        .create(true)
        .append(true)
        .open(&*path);

    match result {
        Ok(mut file) => {
            if let Err(e) = writeln!(file, "{}", req.message) {
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
    
    match read_to_string(&*path) {
        Ok(content) => HttpResponse::Ok().content_type("text/plain").body(content),
        Err(e) => {
            // If file doesn't exist yet, return empty string instead of error
            if e.kind() == std::io::ErrorKind::NotFound {
                HttpResponse::Ok().content_type("text/plain").body("")
            } else {
                HttpResponse::InternalServerError().body(format!("Error reading file: {}", e))
            }
        }
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let app_state = web::Data::new(AppState {
        file_path: Mutex::new("logs.txt".to_string()),
    });

    println!("Starting server on 0.0.0.0:5000...");
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