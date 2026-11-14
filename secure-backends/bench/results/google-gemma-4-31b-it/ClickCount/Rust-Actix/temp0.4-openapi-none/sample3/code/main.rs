use actix_web::{get, post, web, App, HttpResponse, HttpServer, Responder};
use chrono::{DateTime, NaiveDate, Utc};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};
use uuid::Uuid;

// Database wrapper to share across Actix workers
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
    // Validate direction enum
    if !["<", ">", "<=", ">="].contains(&query.direction.as_str()) {
        return HttpResponse::BadRequest().body("Invalid direction");
    }

    // Validate date format (YYYY-MM-DD)
    if NaiveDate::parse_from_str(&query.date, "%Y-%m-%d").is_err() {
        return HttpResponse::BadRequest().body("Invalid date format. Use YYYY-MM-DD");
    }

    let mut conn = data.db.lock().unwrap();
    
    // We construct the query carefully. Since direction is validated against a strict enum, 
    // it is safe to interpolate into the SQL string here.
    let sql = format!("SELECT id, timestamp FROM clicks WHERE timestamp {} ?", query.direction);
    
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
    env_logger::init_from_env(env_logger::Env::new().default_filter_or("info"));

    let db_conn = init_db();
    let app_state = Arc::new(AppState {
        db: Mutex::new(db_conn),
    });

    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(app_state.clone()))
            .service(register_click)
            .service(retrieve_clicks)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}