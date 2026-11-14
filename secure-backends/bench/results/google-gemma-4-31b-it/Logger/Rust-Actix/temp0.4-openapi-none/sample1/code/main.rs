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
    file_path: &'static str,
    lock: Mutex<()>,
}

#[post("/log")]
async fn log_message(data: web::Data<AppState>, req: web::Json<LogRequest>) -> impl Responder {
    let _guard = data.lock.lock().unwrap();
    
    let mut file = match OpenOptions::new()
        .create(true)
        .append(true)
        .open(data.file_path) 
    {
        Ok(f) => f,
        Err(_) => return HttpResponse::InternalServerError().finish(),
    };

    if let Err(_) = writeln!(file, "{}", req.message) {
        return HttpResponse::InternalServerError().finish();
    }

    HttpResponse::Ok().finish()
}

#[get("/logs")]
async fn get_logs(data: web::Data<AppState>) -> impl Responder {
    let _guard = data.lock.lock().unwrap();
    
    match read_to_string(data.file_path) {
        Ok(content) => HttpResponse::Ok().content_type("text/plain").body(content),
        Err(_) => {
            // If file doesn't exist yet, return empty string
            HttpResponse::Ok().content_type("text/plain").body("")
        }
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let app_state = web::Data::new(AppState {
        file_path: "logs.txt",
        lock: Mutex::new(()),
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