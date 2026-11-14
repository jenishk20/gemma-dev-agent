use actix_web::{get, post, web, App, HttpResponse, HttpServer, Responder};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

// --- Models ---

#[derive(Debug, Serialize, Deserialize)]
struct Product {
    name: String,
    #[serde(flatten)]
    properties: HashMap<String, String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct DownloadResponse {
    data: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct UploadRequest {
    name: String,
    data: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct SearchResponse {
    results: Vec<Product>,
}

// --- Database Logic ---

struct DbState {
    conn: Mutex<Connection>,
}

fn init_db() -> Connection {
    let conn = Connection::open("db.sqlite3").expect("Failed to open database");
    conn.execute(
        "CREATE TABLE IF NOT EXISTS products (
            name TEXT PRIMARY KEY,
            properties TEXT NOT NULL
        )",
        [],
    )
    .expect("Failed to create table");
    conn
}

// --- Handlers ---

#[post("/add")]
async fn add_product(state: web::Data<Arc<DbState>>, product: web::Json<Product>) -> impl Responder {
    let product = product.into_inner();
    let props_json = serde_json::to_string(&product.properties).unwrap();

    let conn = state.conn.lock().unwrap();
    let result = conn.execute(
        "INSERT INTO products (name, properties) VALUES (?1, ?2)",
        params![product.name, props_json],
    );

    match result {
        Ok(_) => HttpResponse::Created().finish(),
        Err(_) => HttpResponse::BadRequest().body("Product already exists or invalid input"),
    }
}

#[get("/download")]
async fn download_product(state: web::Data<Arc<DbState>>, query: web::Query<HashMap<String, String>>) -> impl Responder {
    let name = match query.get("name") {
        Some(n) => n,
        None => return HttpResponse::BadRequest().body("Missing name parameter"),
    };

    let conn = state.conn.lock().unwrap();
    let mut stmt = conn
        .prepare("SELECT properties FROM products WHERE name = ?1")
        .unwrap();
    
    let props_json: Result<String, _> = stmt.query_row(params![name], |row| row.get(0));

    match props_json {
        Ok(json) => {
            // The schema says "data of a product". Since we store unstructured properties, 
            // we return the JSON string of the properties map.
            HttpResponse::Ok().json(DownloadResponse { data: json })
        }
        Err(_) => HttpResponse::NotFound().body("Product not found"),
    }
}

#[post("/upload")]
async fn upload_product(state: web::Data<Arc<DbState>>, req: web::Json<UploadRequest>) -> impl Responder {
    let req = req.into_inner();
    
    // Validate that data is valid JSON (as it was produced by /download)
    if serde_json::from_str::<HashMap<String, String>>(&req.data).is_err() {
        return HttpResponse::BadRequest().body("Invalid upload data format");
    }

    let conn = state.conn.lock().unwrap();
    let result = conn.execute(
        "INSERT OR REPLACE INTO products (name, properties) VALUES (?1, ?2)",
        params![req.name, req.data],
    );

    match result {
        Ok(_) => HttpResponse::Ok().body("The product with the given name was updated."),
        Err(_) => HttpResponse::BadRequest().body("Database error"),
    }
}

#[get("/search")]
async fn search_products(state: web::Data<Arc<DbState>>, query: web::Query<HashMap<String, String>>) -> impl Responder {
    let search_term = match query.get("query") {
        Some(q) => q,
        None => return HttpResponse::BadRequest().body("Missing query parameter"),
    };

    let conn = state.conn.lock().unwrap();
    let mut stmt = conn
        .prepare("SELECT name, properties FROM products")
        .unwrap();

    let product_iter = stmt.query_map(params![], |row| {
        let name: String = row.get(0)?;
        let props_raw: String = row.get(1)?;
        let properties: HashMap<String, String> = serde_json::from_str(&props_raw).unwrap_or_default();
        Ok(Product { name, properties })
    })
    .unwrap();

    let mut results = Vec::new();
    for product in product_iter {
        if let Ok(p) = product {
            // Match name or any value in the unstructured properties
            let match_name = p.name.contains(search_term);
            let match_props = p.properties.values().any(|v| v.contains(search_term));
            
            if match_name || match_props {
                results.push(p);
            }
        }
    }

    HttpResponse::Ok().json(SearchResponse { results })
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let db_conn = init_db();
    let state = Arc::new(DbState {
        conn: Mutex::new(db_conn),
    });

    println!("Starting server on 0.0.0.0:5000...");
    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(state.clone()))
            .service(add_product)
            .service(download_product)
            .service(upload_product)
            .service(search_products)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}