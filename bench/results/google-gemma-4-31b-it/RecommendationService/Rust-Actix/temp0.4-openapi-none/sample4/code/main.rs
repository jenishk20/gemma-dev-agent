use actix_web::{get, post, web, App, HttpResponse, HttpServer, Responder};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};

#[derive(Deserialize, Serialize)]
struct Product {
    product_name: String,
    tags: Vec<String>,
}

struct AppState {
    db: Mutex<Connection>,
}

async fn init_db() -> Connection {
    let conn = Connection::open("db.sqlite3").expect("Failed to open database");
    conn.execute(
        "CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
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
async fn get_recommender(
    data: web::Data<AppState>,
    query: web::Query<std::collections::HashMap<String, String>>,
) -> impl Responder {
    let tags_param = match query.get("tags") {
        Some(t) => t,
        None => return HttpResponse::BadRequest().body("Missing tags parameter"),
    };

    let search_tags: Vec<&str> = tags_param.split(',').filter(|s| !s.is_empty()).collect();
    if search_tags.is_empty() {
        return HttpResponse::Ok().body("<html><body>No products found.</body></html>");
    }

    let db = data.db.lock().unwrap();
    let mut stmt = db
        .prepare(
            "SELECT DISTINCT p.name FROM products p 
             JOIN tags t ON p.id = t.product_id 
             WHERE t.tag IN (SELECT value FROM json_each(?1))",
        )
        .unwrap();

    // rusqlite doesn't have a direct "IN" helper for dynamic lists easily without 
    // building the query string or using json_each. 
    // Since we are limited in crates, we'll build a simple query.
    
    let mut results = Vec::new();
    for tag in search_tags {
        let mut stmt = db.prepare(
            "SELECT DISTINCT p.name FROM products p JOIN tags t ON p.id = t.product_id WHERE t.tag = ?1"
        ).unwrap();
        let rows = stmt.query_map([tag], |row| row.get::<_, String>(0)).unwrap();
        for item in rows {
            if let Ok(name) = item {
                if !results.contains(&name) {
                    results.push(name);
                }
            }
        }
    }

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
async fn post_recommender(
    data: web::Data<AppState>,
    product: web::Json<Product>,
) -> impl Responder {
    let db = data.db.lock().unwrap();
    
    let tx = db.unchecked_transaction().expect("Failed to start transaction");
    
    tx.execute("INSERT INTO products (name) VALUES (?1)", params![product.product_name])
        .expect("Failed to insert product");
    
    let product_id = tx.last_insert_rowid();
    
    for tag in &product.tags {
        tx.execute("INSERT INTO tags (product_id, tag) VALUES (?1, ?2)", params![product_id, tag])
            .expect("Failed to insert tag");
    }
    
    tx.commit().expect("Failed to commit transaction");

    HttpResponse::Ok().body("Successful operation")
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let conn = init_db().await;
    let app_state = web::Data::new(AppState {
        db: Mutex::new(conn),
    });

    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .service(get_recommender)
            .service(post_recommender)
    })
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}