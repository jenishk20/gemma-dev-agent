use actix_web::{get, post, web, App, HttpResponse, HttpServer, Responder};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use serde_json::{Value, Map};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

// Database manager to handle SQLite connection
struct DbState {
    conn: Mutex<Connection>,
}

#[derive(Deserialize, Serialize, Debug)]
struct Product {
    name: String,
    #[serde(flatten)]
    properties: HashMap<String, String>,
}

#[derive(Deserialize)]
struct UploadRequest {
    name: String,
    data: String,
}

#[derive(Serialize)]
struct DownloadResponse {
    data: String,
}

#[derive(Serialize)]
struct SearchResponse {
    results: Vec<Product>,
}

// Initialize database and create table
fn init_db() -> Connection {
    let conn = Connection::open("db.sqlite3").expect("Failed to open database");
    conn.execute(
        "CREATE TABLE IF NOT EXISTS products (
            name TEXT PRIMARY KEY,
            properties TEXT NOT NULL
        )",
        [],
    ).expect("Failed to create table");
    conn
}

#[post("/add")]
async fn add_product(data: web::Data<Arc<DbState>>, payload: web::Json<Product>) -> impl Responder {
    let product = payload.into_inner();
    let mut conn = data.conn.lock().unwrap();
    
    // We store the properties (including name) as a JSON string to handle unstructured data
    let mut all_props = product.properties.clone();
    all_props.insert("name".to_string(), product.name.clone());
    let json_data = serde_json::to_string(&all_props).unwrap();

    let result = conn.execute(
        "INSERT OR REPLACE INTO products (name, properties) VALUES (?1, ?2)",
        params![product.name, json_data],
    );

    match result {
        Ok(_) => HttpResponse::Created().finish(),
        Err(_) => HttpResponse::BadRequest().finish(),
    }
}

#[get("/download")]
async fn download_product(data: web::Data<Arc<DbState>>, query: web::Query<HashMap<String, String>>) -> impl Responder {
    let name = match query.get("name") {
        Some(n) => n,
        None => return HttpResponse::BadRequest().finish(),
    };

    let conn = data.conn.lock().unwrap();
    let mut stmt = conn.prepare("SELECT properties FROM products WHERE name = ?1").unwrap();
    let product_data: Result<String, _> = stmt.query_row(params![name], |row| row.get(0));

    match product_data {
        Ok(json_str) => HttpResponse::Ok().json(DownloadResponse { data: json_str }),
        Err(_) => HttpResponse::NotFound().finish(),
    }
}

#[post("/upload")]
async fn upload_product(data: web::Data<Arc<DbState>>, payload: web::Json<UploadRequest>) -> impl Responder {
    let req = payload.into_inner();
    
    // Validate that the data is valid JSON and contains the name
    let parsed: Value = match serde_json::from_str(&req.data) {
        Ok(v) => v,
        Err(_) => return HttpResponse::BadRequest().finish(),
    };

    let mut conn = data.conn.lock().unwrap();
    let result = conn.execute(
        "INSERT OR REPLACE INTO products (name, properties) VALUES (?1, ?2)",
        params![req.name, req.data],
    );

    match result {
        Ok(_) => HttpResponse::Ok().finish(),
        Err(_) => HttpResponse::BadRequest().finish(),
    }
}

#[get("/search")]
async fn search_products(data: web::Data<Arc<DbState>>, query: web::Query<HashMap<String, String>>) -> impl Responder {
    let search_term = match query.get("query") {
        Some(q) => q,
        None => return HttpResponse::BadRequest().finish(),
    };

    let conn = data.conn.lock().unwrap();
    let mut stmt = conn.prepare("SELECT properties FROM products").unwrap();
    let rows = stmt.query_map(params![], |row| {
        let props_json: String = row.get(0)?;
        Ok(props_json)
    }).unwrap();

    let mut results = Vec::new();
    for row in rows {
        if let Ok(json_str) = row {
            if let Ok(map) = serde_json::from_str::<Map<String, Value>>(&json_str) {
                let mut match_found = false;
                for (k, v) in &map {
                    if let Some(val_str) = v.as_str() {
                        if val_str.contains(search_term) {
                            match_found = true;
                            break;
                        }
                    }
                }
                
                if match_found {
                    let mut product_props = HashMap::new();
                    for (k, v) in map {
                        if k != "name" {
                            if let Some(val_str) = v.as_str() {
                                product_props.insert(k, val_str.to_string());
                            }
                        }
                    }
                    
                    // Extract name from the map for the Product struct
                    let name = map.get("name")
                        .and_then(|v| v.as_str())
                        .unwrap_or("Unknown")
                        .to_string();

                    results.push(Product { name, properties: product_props });
                }
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