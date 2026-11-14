use actix_web::{get, post, web, App, HttpResponse, HttpServer, Responder};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};

#[derive(Serialize, Deserialize, Debug)]
struct Message {
    content: String,
    username: String,
}

#[derive(Deserialize)]
struct MessageQuery {
    limit: Option<i64>,
    offset: Option<i64>,
    sort: Option<String>,
}

struct AppState {
    db: Mutex<Connection>,
}

async fn init_db() -> Connection {
    let conn = Connection::open("db.sqlite3").expect("Failed to open database");
    conn.execute(
        "CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )",
        [],
    ).expect("Failed to create table");
    conn
}

#[get("/messages")]
async fn get_messages(data: web::Data<AppState>, query: web::Query<MessageQuery>) -> impl Responder {
    let conn = data.db.lock().unwrap();
    
    let limit = query.limit.unwrap_or(10);
    let offset = query.offset.unwrap_or(0);
    let sort_dir = match query.sort.as_deref() {
        Some("ASC") => "ASC",
        _ => "DESC",
    };

    let sql = format!("SELECT username, content FROM messages ORDER BY created_at {} LIMIT ? OFFSET ?", sort_dir);
    let mut stmt = conn.prepare(&sql).expect("Failed to prepare statement");
    
    let rows = stmt.query_map(params![limit, offset], |row| {
        Ok(Message {
            username: row.get(0)?,
            content: row.get(1)?,
        })
    }).expect("Query failed");

    let mut html = String::from("<html><body><h1>Forum Messages</h1><ul>");
    for row in rows {
        if let Ok(msg) = row {
            html.push_str(&format!("<li><strong>{}</strong>: {}</li>", msg.username, msg.content));
        }
    }
    html.push_str("</ul><hr><form action='/messages' method='POST' enctype='application/json'>");
    html.push_str("<p>Note: This API expects JSON for POST. Use a tool like curl or a JSON client.</p>");
    html.push_str("</body></html>");

    HttpResponse::Ok().content_type("text/html").body(html)
}

#[post("/messages")]
async fn post_message(data: web::Data<AppState>, msg: web::Json<Message>) -> impl Responder {
    let conn = data.db.lock().unwrap();
    let res = conn.execute(
        "INSERT INTO messages (username, content) VALUES (?1, ?2)",
        params![msg.username, msg.content],
    );

    match res {
        Ok(_) => HttpResponse::Ok().body("Successful operation"),
        Err(_) => HttpResponse::BadRequest().body("Invalid input"),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();
    
    let db_conn = init_db().await;
    let app_state = web::Data::new(AppState {
        db: Mutex::new(db_conn),
    });

    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .service(get_messages)
            .service(post_message)
    })
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}