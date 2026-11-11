use actix_web::{get, post, web, App, HttpResponse, HttpServer, Responder};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};

#[derive(Serialize, Deserialize, Debug)]
struct Message {
    content: String,
    username: String,
}

struct AppState {
    db: Mutex<Connection>,
}

#[derive(Deserialize)]
struct MessageQuery {
    limit: Option<i64>,
    offset: Option<i64>,
    sort: Option<String>,
}

#[get("/messages")]
async fn get_messages(data: web::Data<AppState>, query: web::Query<MessageQuery>) -> impl Responder {
    let db = data.db.lock().unwrap();
    
    let limit = query.limit.unwrap_or(10);
    let offset = query.offset.unwrap_or(0);
    let sort_order = match query.sort.as_deref() {
        Some("ASC") => "ASC",
        _ => "DESC",
    };

    let query_str = format!(
        "SELECT username, content FROM messages ORDER BY id {} LIMIT ? OFFSET ?",
        sort_order
    );

    let mut stmt = db.prepare(&query_str).unwrap();
    let message_iter = stmt.query_map(params![limit, offset], |row| {
        Ok(Message {
            username: row.get(0)?,
            content: row.get(1)?,
        })
    }).unwrap();

    let mut html = String::from("<html><body><h1>Forum Messages</h1><ul>");
    for msg in message_iter {
        if let Ok(m) = msg {
            html.push_str(&format!("<li><b>{}</b>: {}</li>", m.username, m.content));
        }
    }
    html.push_str("</ul></body></html>");

    HttpResponse::Ok().content_type("text/html").body(html)
}

#[post("/messages")]
async fn post_message(data: web::Data<AppState>, msg: web::Json<Message>) -> impl Responder {
    let db = data.db.lock().unwrap();
    
    if msg.username.is_empty() || msg.content.is_empty() {
        return HttpResponse::BadRequest().body("Invalid input");
    }

    let result = db.execute(
        "INSERT INTO messages (username, content) VALUES (?1, ?2)",
        params![msg.username, msg.content],
    );

    match result {
        Ok(_) => HttpResponse::Ok().finish(),
        Err(_) => HttpResponse::InternalServerError().finish(),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let conn = Connection::open("db.sqlite3").expect("Failed to open database");
    
    conn.execute(
        "CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            content TEXT NOT NULL
        )",
        [],
    ).expect("Failed to create table");

    let app_state = web::Data::new(AppState {
        db: Mutex::new(conn),
    });

    println!("Starting server at http://0.0.0.0:5000");
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