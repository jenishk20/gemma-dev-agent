use actix_web::{post, web, App, HttpResponse, HttpServer, Responder};
use chrono::{DateTime, Utc};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};

#[derive(Deserialize)]
struct HeartbeatRequest {
    #[serde(rename = "serviceId")]
    service_id: String,
    token: String,
}

#[derive(Deserialize)]
struct ServicesRequest {
    token: String,
}

#[derive(Serialize)]
struct ServiceStatus {
    #[serde(rename = "serviceId")]
    service_id: String,
    #[serde(rename = "lastNotification")]
    last_notification: DateTime<Utc>,
}

struct AppState {
    db: Mutex<Connection>,
}

async fn init_db() -> Connection {
    let conn = Connection::open("db.sqlite3").expect("Failed to open database");
    conn.execute(
        "CREATE TABLE IF NOT EXISTS heartbeats (
            service_id TEXT PRIMARY KEY,
            token TEXT NOT NULL,
            last_notification TEXT NOT NULL
        )",
        [],
    )
    .expect("Failed to create table");
    conn
}

#[post("/heartbeat")]
async fn heartbeat(
    data: web::Data<AppState>,
    payload: web::Json<HeartbeatRequest>,
) -> impl Responder {
    let db = data.db.lock().unwrap();
    let now = Utc::now();
    
    let result = db.execute(
        "INSERT INTO heartbeats (service_id, token, last_notification) 
         VALUES (?1, ?2, ?3) 
         ON CONFLICT(service_id) DO UPDATE SET 
         token = excluded.token, 
         last_notification = excluded.last_notification",
        params![payload.service_id, payload.token, now.to_rfc3339()],
    );

    match result {
        Ok(_) => HttpResponse::Ok().finish(),
        Err(_) => HttpResponse::InternalServerError().finish(),
    }
}

#[post("/services")]
async fn get_services(
    data: web::Data<AppState>,
    payload: web::Json<ServicesRequest>,
) -> impl Responder {
    let db = data.db.lock().unwrap();
    
    let mut stmt = match db.prepare("SELECT service_id, last_notification FROM heartbeats WHERE token = ?1") {
        Ok(s) => s,
        Err(_) => return HttpResponse::InternalServerError().finish(),
    };

    let rows = stmt.query_map(params![payload.token], |row| {
        let id: String = row.get(0)?;
        let date_str: String = row.get(1)?;
        let date = DateTime::parse_from_rfc3339(&date_str)
            .expect("Invalid date format in DB")
            .with_timezone(&Utc);
        
        Ok(ServiceStatus {
            service_id: id,
            last_notification: date,
        })
    });

    match rows {
        Ok(iter) => {
            let services: Vec<ServiceStatus> = iter
                .filter_map(|res| res.ok())
                .collect();
            HttpResponse::Ok().json(services)
        }
        Err(_) => HttpResponse::InternalServerError().finish(),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let conn = init_db().await;
    let app_state = web::Data::new(AppState {
        db: Mutex::new(conn),
    });

    println!("Starting server on 0.0.0.0:5000");
    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .service(heartbeat)
            .service(get_services)
    })
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}