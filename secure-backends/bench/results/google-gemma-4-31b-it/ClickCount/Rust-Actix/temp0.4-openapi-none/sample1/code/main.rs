use actix_web::{get, post, web, App, HttpResponse, HttpServer, Responder};
use chrono::{DateTime, NaiveDate, Utc};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};
use uuid::Uuid;

// --- Models ---

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

// --- Database Management ---

struct DbState {
    conn: Mutex<Connection>,
}

fn init_db() -> Connection {
    let conn = Connection::open("db.sqlite3").expect("Failed to open database");
    conn.execute(
        "CREATE TABLE IF NOT EXISTS clicks (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL
        )",
        [],
    )
    .expect("Failed to create table");
    conn
}

// --- Handlers ---

#[post("/click")]
async fn register_click(data: web::Data<Arc<DbState>>) -> impl Responder {
    let id = Uuid::new_v4().to_string();
    let timestamp = Utc::now().to_rfc3339();

    let conn = data.conn.lock().unwrap();
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
async fn retrieve_clicks(data: web::Data<Arc<DbState>>, query: web::Query<ClickQuery>) -> impl Responder {
    // Validate direction enum
    let valid_directions = ["<", ">", "<=", ">="];
    if !valid_directions.contains(&query.direction.as_str()) {
        return HttpResponse::BadRequest().body("Invalid direction. Use <, >, <=, or >=");
    }

    // Validate date format (YYYY-MM-DD)
    if NaiveDate::parse_from_str(&query.date, "%Y-%m-%d").is_err() {
        return HttpResponse::BadRequest().body("Invalid date format. Use YYYY-MM-DD");
    }

    let conn = data.conn.lock().unwrap();
    
    // Construct SQL query safely. 
    // Note: We validate the direction against a whitelist to prevent SQL injection 
    // since operators cannot be parameterized in SQLite.
    let sql = format!(
        "SELECT id, timestamp FROM clicks WHERE date(timestamp) {} ?1",
        query.direction
    );

    let mut stmt = match conn.prepare(&sql) {
        Ok(s) => s,
        Err(_) => return HttpResponse::InternalServerError().finish(),
    };

    let click_iter = stmt.query_map(params![query.date], |row| {
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
    env_logger::init();

    let db_conn = init_db();
    let state = Arc::new(DbState {
        conn: Mutex::new(db_conn),
    });

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