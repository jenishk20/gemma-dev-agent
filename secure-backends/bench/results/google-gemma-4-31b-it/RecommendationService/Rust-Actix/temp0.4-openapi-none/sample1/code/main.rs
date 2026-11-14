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
struct SearchQuery {
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
async fn get_recommendations(data: web::Data<AppState>, query: web::Query<SearchQuery>) -> impl Responder {
    let conn = data.db.lock().unwrap();
    let search_tags: Vec<&str> = query.tags.split(',').map(|s| s.trim()).filter(|s| !s.is_empty()).collect();

    if search_tags.is_empty() {
        return HttpResponse::Ok().content_type("text/html").body("<ul></ul>".to_string());
    }

    // Build a query to find products that have at least one of the tags
    let mut sql = "SELECT DISTINCT p.name FROM products p JOIN tags t ON p.id = t.product_id WHERE t.tag".to_string();
    for i in 0..search_tags.len() {
        sql.push_str(" ? ");
        if i < search_tags.len() - 1 {
            sql.push_str(" OR t.tag ");
        }
    }

    let mut stmt = match conn.prepare(&sql) {
        Ok(s) => s,
        Err(_) => return HttpResponse::InternalServerError().finish(),
    };

    let product_iter = stmt.query_map(rusqlite::params_from_iter(search_tags), |row| {
        row.get::<_, String>(0)
    });

    let mut html_output = String::from("<html><body><ul>");
    if let Ok(rows) = product_iter {
        for product in rows.flatten() {
            html_output.push_str(&format!("<li>{}</li>", product));
        }
    }
    html_output.push_str("</ul></body></html>");

    HttpResponse::Ok().content_type("text/html").body(html_output)
}

#[post("/recommender")]
async fn post_product(data: web::Data<AppState>, payload: web::Json<ProductRequest>) -> impl Responder {
    let conn = data.db.lock().unwrap();
    
    if payload.product_name.is_empty() {
        return HttpResponse::BadRequest().body("Invalid input: product_name is required");
    }

    let tx = match conn.unchecked_transaction() {
        Ok(t) => t,
        Err(_) => return HttpResponse::InternalServerError().finish(),
    };

    let res = tx.execute("INSERT INTO products (name) VALUES (?)", params![payload.product_name]);
    
    match res {
        Ok(id) => {
            let product_id = conn.last_insert_rowid();
            for tag in &payload.tags {
                if let Err(_) = conn.execute("INSERT INTO tags (product_id, tag) VALUES (?, ?)", params![product_id, tag]) {
                    return HttpResponse::InternalServerError().finish();
                }
            }
            HttpResponse::Ok().finish()
        }
        Err(_) => HttpResponse::InternalServerError().finish(),
    }
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
            .service(get_recommendations)
            .service(post_product)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}