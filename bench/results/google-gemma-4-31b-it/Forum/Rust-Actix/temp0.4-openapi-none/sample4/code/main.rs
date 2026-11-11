use actix_web::{get, post, web, App, HttpResponse, HttpServer, Responder};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};

#[derive(Serialize, Deserialize, Debug)]
struct Message {
    username: String,
    content: String,
}

#[derive(Deserialize)]
struct MessageQuery {
    #[serde(default = "default_limit")]
    limit: i64,
    #[serde(default = "default_offset")]
    offset: i64,
    #[serde(default = "default_sort")]
    sort: String,
}

fn default_limit() -> i64 { 10 }
fn default_offset() -> i64 { 0 }
fn default_sort() -> String { "DESC".to_string() }

struct AppState {
    db: Mutex<Connection>,
}

#[get("/messages")]
async fn get_messages(data: web::Data<AppState>, query: web::Query<MessageQuery>) -> impl Responder {
    let db = data.db.lock().unwrap();
    
    let sort_order = if query.sort.to_uppercase() == "ASC" { "ASC" } else { "DESC" };
    let sql = format!("SELECT username, content FROM messages ORDER BY id {} LIMIT ? OFFSET ?", sort_order);
    
    let mut stmt = match db.prepare(&sql) {
        Ok(s) => s,
        Err(_) => return HttpResponse::InternalServerError().body("Database error"),
    };

    let rows = stmt.query_map(params![query.limit, query.offset], |row| {
        Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
    }).unwrap();

    let mut html = String::from("<html><body><h1>Forum Messages</h1><ul>");
    for row in rows {
        if let Ok((user, msg)) = row {
            html.push_str(&format!("<li><strong>{}</strong>: {}</li>", user, msg));
        }
    }
    html.push_str("</ul><hr><form method='POST' action='/messages'>Username: <input name='username'><br>Message: <input name='content'><br><input type='submit'></form></body></html>");

    HttpResponse::Ok().content_type("text/html").body(html)
}

#[post("/messages")]
async fn post_message(data: web::Data<AppState>, msg: web::Json<Message>) -> impl Responder {
    let db = data.db.lock().unwrap();
    let res = db.execute(
        "INSERT INTO messages (username, content) VALUES (?1, ?2)",
        params![msg.username, msg.content],
    );

    match res {
        Ok(_) => HttpResponse::Ok().finish(),
        Err(_) => HttpResponse::BadRequest().finish(),
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

    println!("Server starting on 0.0.0.0:5000");
    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .service(get_messages)
            .service(post_message)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}