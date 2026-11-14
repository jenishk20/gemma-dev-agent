use actix_web::{get, post, web, App, HttpResponse, HttpServer, Responder};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};

#[derive(Deserialize)]
struct ProductRequest {
    product_name: String,
    tags: Vec<String>,
}

#[derive(Deserialize)]
struct TagsQuery {
    tags: String,
}

struct AppState {
    db: Mutex<Connection>,
}

fn init_db() -> Connection {
    let conn = Connection::open("db.sqlite3").expect("Failed to open database");
    conn.execute(
        "CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )",
        [],
    ).expect("Failed to create products table");
    conn.execute(
        "CREATE TABLE IF NOT EXISTS tags (
            product_id INTEGER,
            tag TEXT NOT NULL,
            FOREIGN KEY(product_id) REFERENCES products(id)
        )",
        [],
    ).expect("Failed to create tags table");
    conn
}

#[get("/recommender")]
async fn get_recommender(data: web::Data<AppState>, query: web::Query<TagsQuery>) -> impl Responder {
    let tags: Vec<&str> = query.tags.split(',').filter(|s| !s.is_empty()).collect();
    if tags.is_empty() {
        return HttpResponse::Ok().content_type("text/html").body("<h1>No tags provided</h1>");
    }

    let db = data.db.lock().unwrap();
    
    // Query to find products that have at least one of the tags
    let mut stmt = db.prepare(
        "SELECT DISTINCT p.name FROM products p 
         JOIN tags t ON p.id = t.product_id 
         WHERE t.tag IN (SELECT value FROM json_each(?))"
    ).unwrap();

    // We use a simple approach for the IN clause since rusqlite doesn't support dynamic lists easily 
    // without building the query string. For safety and simplicity, we'll iterate or use a manual query.
    let mut results = Vec::new();
    for tag in tags {
        let mut stmt = db.prepare("SELECT p.name FROM products p JOIN tags t ON p.id = t.product_id WHERE t.tag = ?").unwrap();
        let rows = stmt.query_map([tag], |row| {
            let name: String = row.get(0).unwrap();
            Ok(name)
        }).unwrap();
        for name in rows {
            results.push(name.unwrap());
        }
    }

    // Deduplicate results
    results.sort();
    results.dedup();

    let mut html = String::from("<html><body><h1>Recommended Products</h1><ul>");
    if results.is_empty() {
        html.push_str("<li>No products found matching those tags.</li>");
    } else {
        for product in results {
            html.push_str(&format!("<li>{}</li>", product));
        }
    }
    html.push_str("</ul></body></html>");

    HttpResponse::Ok().content_type("text/html").body(html)
}

#[post("/recommender")]
async fn post_recommender(data: web::Data<AppState>, payload: web::Json<ProductRequest>) -> impl Responder {
    let db = data.db.lock().unwrap();
    
    let tx = db.unchecked_transaction().expect("Failed to start transaction");
    
    tx.execute("INSERT INTO products (name) VALUES (?)", params![payload.product_name])
        .expect("Failed to insert product");
    
    let product_id = tx.last_insert_rowid();
    
    for tag in &payload.tags {
        tx.execute("INSERT INTO tags (product_id, tag) VALUES (?, ?)", params![product_id, tag])
            .expect("Failed to insert tag");
    }
    
    tx.commit().expect("Failed to commit transaction");

    HttpResponse::Ok().finish()
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let db_conn = init_db();
    let app_state = web::Data::new(AppState {
        db: Mutex::new(db_conn),
    });

    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .service(get_recommender)
            .service(post_recommender)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}