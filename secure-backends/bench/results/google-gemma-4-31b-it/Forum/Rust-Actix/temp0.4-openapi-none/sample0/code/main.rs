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
struct PaginationQuery {
    limit: Option<i64>,
    offset: Option<i64>,
    sort: Option<String>,
}

struct AppState {
    db: Mutex<Connection>,
}

fn init_db() -> Connection {
    let conn = Connection::open("db.sqlite3").expect("Failed to open database");
    conn.execute(
        "CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )",
        [],
    )
    .expect("Failed to create table");
    conn
}

#[get("/messages")]
async fn get_messages(data: web::Data<AppState>, query: web::Query<PaginationQuery>) -> impl Responder {
    let conn = data.db.lock().unwrap();
    
    let limit = query.limit.unwrap_or(10);
    let offset = query.offset.unwrap_or(0);
    let sort_order = match query.sort.as_deref() {
        Some("ASC") => "ASC",
        _ => "DESC",
    };

    let mut stmt = conn
        .prepare(&format!("SELECT username, content FROM messages ORDER BY created_at {} LIMIT ? OFFSET ?", sort_order))
        .unwrap();

    let message_iter = stmt.query_map(params![limit, offset], |row| {
        Ok(Message {
            username: row.get(0)?,
            content: row.get(1)?,
        })
    }).unwrap();

    let mut html = String::from("<html><body><h1>Forum Messages</h1><ul>");
    for msg in message_iter {
        if let Ok(m) = msg {
            html.push_str(&format!("<li><strong>{}</strong>: {}</li>", m.username, m.content));
        }
    }
    html.push_str("</ul><hr><form method='POST' action='/messages'><input name='username' placeholder='Username'><br><input name='content' placeholder='Message'><br><button type='submit'>Post</button></form></body></html>");

    HttpResponse::Ok().content_type("text/html").body(html)
}

#[post("/messages")]
async fn post_message(data: web::Data<AppState>, msg: web::Json<Message>) -> impl Responder {
    let conn = data.db.lock().unwrap();
    let result = conn.execute(
        "INSERT INTO messages (username, content) VALUES (?1, ?2)",
        params![msg.username, msg.content],
    );

    match result {
        Ok(_) => HttpResponse::Ok().finish(),
        Err(_) => HttpResponse::BadRequest().finish(),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();
    
    let db_conn = init_db();
    let state = web::Data::new(AppState {
        db: Mutex::new(db_conn),
    });

    println!("Server starting on 0.0.0.0:5000");
    HttpServer::new(move || {
        App::new()
            .app_data(state.clone())
            .service(get_messages)
            .service(post_message)
    })
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}