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

// --- Database Logic ---

struct DbState {
    conn: Mutex<Connection>,
}

fn init_db() -> Connection {
    let conn = Connection::open("db.sqlite3").expect("Failed to open database");
    conn.execute(
        "CREATE TABLE IF NOT EXISTS heartbeats (
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
    data: web::Data<Arc<DbState>>,
    payload: web::Json<HeartbeatRequest>,
) -> impl Responder {
    let mut conn = data.conn.lock().unwrap();
    let now = Utc::now().to_rfc3339();

    let result = conn.execute(
        "INSERT INTO heartbeats (service_id, token, last_notification) 
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
    data: web::Data<Arc<DbState>>,
    payload: web::Json<ServicesRequest>,
) -> impl Responder {
    let conn = data.conn.lock().unwrap();
    
    let mut stmt = match conn.prepare("SELECT service_id, last_notification FROM heartbeats WHERE token = ?1") {
        Ok(s) => s,
        Err(_) => return HttpResponse::InternalServerError().finish(),
    };

    let rows = stmt.query_map(params![payload.token], |row| {
        let date_str: String = row.get(1)?;
        let last_notification = date_str.parse::<DateTime<Utc>>().unwrap_or_else(|_| Utc::now());
        Ok(ServiceStatus {
            service_id: row.get(0)?,
            last_notification,
        })
    });

    match rows {
        Ok(iter) => {
            let services: Vec<ServiceStatus> = iter.filter_map(|r| r.ok()).collect();
            HttpResponse::Ok().json(services)
        }
        Err(_) => HttpResponse::InternalServerError().finish(),
    }
}

// --- Main ---

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init_from_env(env_logger::Env::default().default_filter_or("info"));

    let db_conn = init_db();
    let state = Arc::new(DbState {
        conn: Mutex::new(db_conn),
    });

    println!("Starting server on 0.0.0.0:5000");
    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(state.clone()))
            .service(heartbeat)
            .service(get_services)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}