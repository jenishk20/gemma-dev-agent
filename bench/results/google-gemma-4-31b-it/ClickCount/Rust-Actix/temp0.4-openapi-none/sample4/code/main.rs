use actix_web::{get, post, web, App, HttpResponse, HttpServer, Responder};
use chrono::{NaiveDate, Utc};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};
use uuid::Uuid;

// Database wrapper to handle thread-safe access to SQLite
struct AppState {
    db: Mutex<Connection>,
}

#[derive(Serialize, Deserialize)]
struct Click {
    id: String,
    timestamp: String,
}

#[derive(Deserialize)]
struct ClickQuery {
    date: String,
    direction: String,
}

#[post("/click")]
async fn register_click(data: web::Data<Arc<AppState>>) -> impl Responder {
    let mut conn = data.db.lock().unwrap();
    
    let id = Uuid::new_v4().to_string();
    let timestamp = Utc::now().to_rfc3339();

    let result = conn.execute(
        "INSERT INTO clicks (id, timestamp) VALUES (?1, ?2)",
        params![id, timestamp],
    );

    match result {
        Ok(_) => HttpResponse::Created().finish(),
        Err(_) => HttpResponse::BadRequest().finish(),
    }
}

#[get("/clicks")]
async fn retrieve_clicks(data: web::Data<Arc<AppState>>, query: web::Query<ClickQuery>) -> impl Responder {
    let conn = data.db.lock().unwrap();
    
    // Validate date format
    if NaiveDate::parse_from_str(&query.date, "%Y-%m-%d").is_err() {
        return HttpResponse::BadRequest().body("Invalid date format. Expected YYYY-MM-DD");
    }

    // Validate direction operator to prevent SQL injection
    let allowed_operators = ["<", ">", "<=", ">="];
    if !allowed_operators.contains(&query.direction.as_str()) {
        return HttpResponse::BadRequest().body("Invalid direction operator");
    }

    // SQLite stores dates as strings. We compare the timestamp (ISO8601) with the date.
    // We append 'T00:00:00' to the date to ensure correct comparison with timestamps.
    let date_filter = format!("{}T00:00:00", query.date);
    let sql = format!(
        "SELECT id, timestamp FROM clicks WHERE timestamp {} ?1",
        query.direction
    );

    let mut stmt = match conn.prepare(&sql) {
        Ok(s) => s,
        Err(_) => return HttpResponse::InternalServerError().finish(),
    };

    let click_iter = stmt.query_map(params![date_filter], |row| {
        Ok(Click {
            id: row.get(0)?,
            timestamp: row.get(1)?,
        })
    });

    match click_iter {
        Ok(rows) => {
            let mut clicks = Vec::new();
            for row in rows {
                if let Ok(click) = row {
                    clicks.push(click);
                }
            }
            
            if clicks.is_empty() {
                HttpResponse::NotFound().finish()
            } else {
                HttpResponse::Ok().json(clicks)
            }
        }
        Err(_) => HttpResponse::InternalServerError().finish(),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // Initialize Database
    let conn = Connection::open("db.sqlite3").expect("Failed to open database");
    conn.execute(
        "CREATE TABLE IF NOT EXISTS clicks (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL
        )",
        [],
    ).expect("Failed to create table");

    let state = Arc::new(AppState {
        db: Mutex::new(conn),
    });

    println!("Server starting on 0.0.0.0:5000");
    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(state.clone()))
            .service(register_click)
            .service(retrieve_clicks)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}