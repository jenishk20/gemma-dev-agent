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
async fn log_message(data: web::Data<AppState>, req: web::Json<LogRequest>) -> impl Responder {
    let path = data.file_path.lock().unwrap();
    
    let result = OpenOptions::new()
        .create(true)
        .append(true)
        .open(&*path)
        .and_then(|mut file| {
            writeln!(file, "{}", req.message)?;
            Ok::<(), std::io::Error>(())
        });

    match result {
        Ok(_) => HttpResponse::Ok().finish(),
        Err(_) => HttpResponse::InternalServerError().finish(),
    }
}

#[get("/logs")]
async fn get_logs(data: web::Data<AppState>) -> impl Responder {
    let path = data.file_path.lock().unwrap();
    
    match read_to_string(&*path) {
        Ok(contents) => HttpResponse::Ok().content_type("text/plain").body(contents),
        Err(_) => {
            // If file doesn't exist yet, return empty string
            HttpResponse::Ok().content_type("text/plain").body("")
        }
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