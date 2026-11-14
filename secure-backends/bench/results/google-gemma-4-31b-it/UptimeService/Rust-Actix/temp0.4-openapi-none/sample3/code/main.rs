use actix_web::{post, web, App, HttpResponse, HttpServer, Responder};
use chrono::{DateTime, Utc};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};

// --- Models ---

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

// --- Database State ---

struct AppState {
    db: Arc<Mutex<Connection>>,
}

fn init_db() -> Connection {
    let conn = Connection::open("db.sqlite3").expect("Failed to open database");
    conn.execute(
        "CREATE TABLE IF NOT EXISTS services (
            service_id TEXT PRIMARY KEY,
            token TEXT NOT NULL,
            last_notification TEXT NOT NULL
        )",
        [],
    ).expect("Failed to create table");
    conn
}

// --- Handlers ---

#[post("/heartbeat")]
async fn heartbeat(
    data: web::Data<AppState>,
    payload: web::Json<HeartbeatRequest>,
) -> impl Responder {
    let db = data.db.lock().unwrap();
    let now = Utc::now().to_rfc3339();

    let result = db.execute(
        "INSERT INTO services (service_id, token, last_notification) 
         VALUES (?1, ?2, ?3) 
         ON CONFLICT(service_id) DO UPDATE SET 
         token = excluded.token, 
         last_notification = excluded.last_notification",
        params![payload.service_id, payload.token, now],
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
    
    let mut stmt = match db.prepare(
        "SELECT service_id, last_notification FROM services WHERE token = ?1"
    ) {
        Ok(s) => s,
        Err(_) => return HttpResponse::InternalServerError().finish(),
    };

    let rows = stmt.query_map(params![payload.token], |row| {
        let date_str: String = row.get(1)?;
        let last_notification = DateTime::parse_from_rfc3339(&date_str)
            .map(|dt| dt.with_timezone(&Utc))
            .unwrap_or_else(|_| Utc::now());

        Ok(ServiceStatus {
            service_id: row.get(0)?,
            last_notification,
        })
    });

    match rows {
        Ok(mapped_rows) => {
            let mut services = Vec::new();
            for row in mapped_rows {
                if let Ok(s) = row {
                    services.push(s);
                }
            }
            HttpResponse::Ok().json(services)
        }
        Err(_) => HttpResponse::InternalServerError().finish(),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init_from_env(env_logger::Env::new().name("rusqlite"));

    let conn = init_db();
    let app_state = web::Data::new(AppState {
        db: Arc::new(Mutex::new(conn)),
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