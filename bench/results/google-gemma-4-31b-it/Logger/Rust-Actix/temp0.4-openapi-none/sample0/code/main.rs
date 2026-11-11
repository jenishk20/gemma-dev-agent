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
    
    let mut file = match OpenOptions::new()
        .create(true)
        .append(true)
        .open(path.as_str()) 
    {
        Ok(f) => f,
        Err(_) => return HttpResponse::InternalServerError().body("Error opening log file"),
    };

    if let Err(_) = writeln!(file, "{}", req.message) {
        return HttpResponse::InternalServerError().body("Error writing to log file");
    }

    HttpResponse::Ok().finish()
}

#[get("/logs")]
async fn get_logs(data: web::Data<AppState>) -> impl Responder {
    let path = data.file_path.lock().unwrap();
    
    match read_to_string(path.as_str()) {
        Ok(content) => HttpResponse::Ok().content_type("text/plain").body(content),
        Err(_) => HttpResponse::InternalServerError().body("Error reading log file"),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let state = web::Data::new(AppState {
        file_path: Mutex::new("logs.txt".to_string()),
    });

    HttpServer::new(move || {
        App::new()
            .app_data(state.clone())
            .service(log_message)
            .service(get_logs)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}