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
async fn get_recommendations(data: web::Data<AppState>, query: web::Query<TagsQuery>) -> impl Responder {
    let tags_list: Vec<&str> = query.tags.split(',').map(|s| s.trim()).filter(|s| !s.is_empty()).collect();
    
    if tags_list.is_empty() {
        return HttpResponse::Ok().content_type("text/html").body("<h1>No tags provided</h1>");
    }

    let db = data.db.lock().unwrap();
    
    // Query to find products that have at least one of the provided tags
    let mut stmt = db.prepare(
        "SELECT DISTINCT p.name FROM products p 
         JOIN tags t ON p.id = t.product_id 
         WHERE t.tag IN (SELECT value FROM json_each(?1))"
    ).unwrap();

    // We use json_each for a dynamic list of tags in SQLite
    let tags_json = serde_json::to_string(&tags_list).unwrap();
    let product_iter = stmt.query_map(params![tags_json], |row| {
        row.get::<_, String>(0)
    }).unwrap();

    let mut html_output = String::from("<html><body><h1>Recommended Products</h1><ul>");
    let mut found = false;

    for product in product_iter {
        if let Ok(name) = product {
            html_output.push_str(&format!("<li>{}</li>", name));
            found = true;
        }
    }

    if !found {
        html_output.push_str("<li>No products found matching those tags.</li>");
    }

    html_output.push_str("</ul></body></html>");

    HttpResponse::Ok().content_type("text/html").body(html_output)
}

#[post("/recommender")]
async fn post_product(data: web::Data<AppState>, product: web::Json<ProductRequest>) -> impl Responder {
    let db = data.db.lock().unwrap();
    
    let tx = db.unchecked_transaction().expect("Failed to start transaction");
    
    tx.execute("INSERT INTO products (name) VALUES (?)", params![product.product_name]).expect("Failed to insert product");
    let product_id = tx.last_insert_rowid();

    for tag in &product.tags {
        tx.execute("INSERT INTO tags (product_id, tag) VALUES (?, ?)", params![product_id, tag]).expect("Failed to insert tag");
    }
    
    tx.commit().expect("Failed to commit transaction");

    HttpResponse::Ok().body("Successful operation")
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let conn = init_db().await;
    let state = web::Data::new(AppState {
        db: Mutex::new(conn),
    });

    HttpServer::new(move || {
        App::new()
            .app_data(state.clone())
            .service(get_recommendations)
            .service(post_product)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}