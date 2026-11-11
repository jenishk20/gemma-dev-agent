use actix_web::{get, post, put, web, App, HttpResponse, HttpServer, Responder};
use chrono::{DateTime, Utc};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};
use uuid::Uuid;

// --- Models ---

#[derive(Serialize, Deserialize, Clone)]
struct Entry {
    id: String,
    title: String,
    content: String,
    last_modified_by: String,
    last_modified_at: String,
}

#[derive(Deserialize)]
struct NewEntry {
    title: String,
    content: String,
    created_by: String,
}

#[derive(Deserialize)]
struct UpdateEntry {
    content: String,
    modified_by: String,
    summary: String,
}

struct AppState {
    db: Mutex<Connection>,
}

// --- Database Helpers ---

fn init_db() -> Connection {
    let conn = Connection::open("db.sqlite3").expect("Failed to open database");
    conn.execute(
        "CREATE TABLE IF NOT EXISTS entries (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            last_modified_by TEXT NOT NULL,
            last_modified_at TEXT NOT NULL
        )",
        [],
    ).expect("Failed to create entries table");

    conn.execute(
        "CREATE TABLE IF NOT EXISTS edits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id TEXT NOT NULL,
            content TEXT NOT NULL,
            modified_by TEXT NOT NULL,
            summary TEXT NOT NULL,
            modified_at TEXT NOT NULL,
            FOREIGN KEY(entry_id) REFERENCES entries(id)
        )",
        [],
    ).expect("Failed to create edits table");

    conn
}

// --- Handlers ---

#[get("/entries")]
async fn get_entries(data: web::Data<AppState>) -> impl Responder {
    let conn = data.db.lock().unwrap();
    let mut stmt = conn
        .prepare("SELECT id, title FROM entries")
        .unwrap();
    
    let rows = stmt.query_map([], |row| {
        Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
    }).unwrap();

    let mut html = String::from("<h1>Wiki Entries</h1><ul>");
    for row in rows {
        if let Ok((id, title)) = row {
            html.push_str(&format!("<li><a href='/entries/{}'>{}</a></li>", id, title));
        }
    }
    html.push_str("</ul><br><a href='/new'>Create New Entry</a>");

    HttpResponse::Ok().content_type("text/html").body(html)
}

#[post("/entries")]
async fn create_entry(data: web::Data<AppState>, payload: web::Json<NewEntry>) -> impl Responder {
    let conn = data.db.lock().unwrap();
    let id = Uuid::new_v4().to_string();
    let now = Utc::now().to_rfc3339();

    conn.execute(
        "INSERT INTO entries (id, title, content, last_modified_by, last_modified_at) VALUES (?1, ?2, ?3, ?4, ?5)",
        params![id, payload.title, payload.content, payload.created_by, now],
    ).unwrap();

    conn.execute(
        "INSERT INTO edits (entry_id, content, modified_by, summary, modified_at) VALUES (?1, ?2, ?3, ?4, ?5)",
        params![id, payload.content, payload.created_by, "Initial creation", now],
    ).unwrap();

    let entry = Entry {
        id,
        title: payload.title.clone(),
        content: payload.content.clone(),
        last_modified_by: payload.created_by.clone(),
        last_modified_at: now,
    };

    HttpResponse::Created().json(entry)
}

#[get("/entries/{entryId}")]
async fn get_entry(data: web::Data<AppState>, path: web::Path<String>) -> impl Responder {
    let entry_id = path.into_inner();
    let conn = data.db.lock().unwrap();
    
    let entry = conn.query_row(
        "SELECT id, title, content, last_modified_by, last_modified_at FROM entries WHERE id = ?1",
        params![entry_id],
        |row| {
            Ok(Entry {
                id: row.get(0)?,
                title: row.get(1)?,
                content: row.get(2)?,
                last_modified_by: row.get(3)?,
                last_modified_at: row.get(4)?,
            })
        },
    );

    match entry {
        Ok(e) => {
            let html = format!(
                "<h1>{}</h1><p>Last modified by {} at {}</p><div>{}</div><hr><a href='/entries/{} /edits'>View History</a>",
                e.title, e.last_modified_by, e.last_modified_at, e.content, e.id
            );
            HttpResponse::Ok().content_type("text/html").body(html)
        }
        Err(_) => HttpResponse::NotFound().body("Entry not found"),
    }
}

#[put("/entries/{entryId}")]
async fn update_entry(data: web::Data<AppState>, path: web::Path<String>, payload: web::Json<UpdateEntry>) -> impl Responder {
    let entry_id = path.into_inner();
    let conn = data.db.lock().unwrap();
    let now = Utc::now().to_rfc3339();

    let updated = conn.execute(
        "UPDATE entries SET content = ?1, last_modified_by = ?2, last_modified_at = ?3 WHERE id = ?4",
        params![payload.content, payload.modified_by, now, entry_id],
    );

    match updated {
        Ok(0) => return HttpResponse::NotFound().body("Entry not found"),
        Ok(_) => {
            conn.execute(
                "INSERT INTO edits (entry_id, content, modified_by, summary, modified_at) VALUES (?1, ?2, ?3, ?4, ?5)",
                params![entry_id, payload.content, payload.modified_by, payload.summary, now],
            ).unwrap();

            let entry = conn.query_row(
                "SELECT id, title, content, last_modified_by, last_modified_at FROM entries WHERE id = ?1",
                params![entry_id],
                |row| {
                    Ok(Entry {
                        id: row.get(0)?,
                        title: row.get(1)?,
                        content: row.get(2)?,
                        last_modified_by: row.get(3)?,
                        last_modified_at: row.get(4)?,
                    })
                },
            ).unwrap();

            HttpResponse::Ok().json(entry)
        }
        Err(_) => HttpResponse::InternalServerError().finish(),
    }
}

#[get("/entries/{entryId}/edits")]
async fn get_edits(data: web::Data<AppState>, path: web::Path<String>) -> impl Responder {
    let entry_id = path.into_inner();
    let conn = data.db.lock().unwrap();

    let mut stmt = conn
        .prepare("SELECT content, modified_by, summary, modified_at FROM edits WHERE entry_id = ?1 ORDER BY modified_at DESC")
        .unwrap();
    
    let rows = stmt.query_map(params![entry_id], |row| {
        Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?, row.get::<_, String>(2)?, row.get::<_, String>(3)?))
    }).unwrap();

    let mut html = format!("<h1>Edit History for {}</h1><ul>", entry_id);
    let mut found = false;
    for row in rows {
        if let Ok((content, user, summary, date)) = row {
            found = true;
            html.push_str(&format!("<li><b>{}</b> ({}) - Summary: {}<br><pre>{}</pre></li><hr>", user, date, summary, content));
        }
    }
    html.push_str("</ul>");

    if !found {
        HttpResponse::NotFound().body("Entry not found or no edits available")
    } else {
        HttpResponse::Ok().content_type("text/html").body(html)
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
            .service(get_entries)
            .service(create_entry)
            .service(get_entry)
            .service(update_entry)
            .service(get_edits)
    })
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}