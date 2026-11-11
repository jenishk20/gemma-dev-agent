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

#[derive(Debug, Deserialize)]
struct UploadRequest {
    name: String,
    data: String,
}

#[derive(Debug, Serialize)]
struct DownloadResponse {
    data: String,
}

#[derive(Debug, Serialize)]
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
async fn add_product(state: web::Data<Arc<DbState>>, item: web::Json<Product>) -> impl Responder {
    let product = item.into_inner();
    let properties_json = serde_json::to_string(&product.properties).unwrap();

    let conn = state.conn.lock().unwrap();
    let result = conn.execute(
        "INSERT OR REPLACE INTO products (name, properties) VALUES (?1, ?2)",
        params![product.name, properties_json],
    );

    match result {
        Ok(_) => HttpResponse::Created().finish(),
        Err(_) => HttpResponse::BadRequest().finish(),
    }
}

#[get("/download")]
async fn download_product(state: web::Data<Arc<DbState>>, query: web::Query<HashMap<String, String>>) -> impl Responder {
    let name = match query.get("name") {
        Some(n) => n,
        None => return HttpResponse::BadRequest().finish(),
    };

    let conn = state.conn.lock().unwrap();
    let mut stmt = conn
        .prepare("SELECT properties FROM products WHERE name = ?1")
        .unwrap();
    
    let res = stmt.query_row(params![name], |row| row.get::<_, String>(0));

    match res {
        Ok(props_json) => {
            // The schema says "the data of a product". 
            // Since we store unstructured properties, we return the JSON representation of the product.
            let mut product_map = HashMap::new();
            product_map.insert("name".to_string(), name.clone());
            
            let props: HashMap<String, String> = serde_json::from_str(&props_json).unwrap_or_default();
            for (k, v) in props {
                product_map.insert(k, v);
            }
            
            let data_string = serde_json::to_string(&product_map).unwrap();
            HttpResponse::Ok().json(DownloadResponse { data: data_string })
        }
        Err(_) => HttpResponse::BadRequest().finish(),
    }
}

#[post("/upload")]
async fn upload_product(state: web::Data<Arc<DbState>>, item: web::Json<UploadRequest>) -> impl Responder {
    let req = item.into_inner();
    
    // The data must be in the format returned by /download (a JSON string representing the product)
    // We need to extract the properties (excluding the name) to store them in our properties column
    let parsed_data: Result<HashMap<String, String>, _> = serde_json::from_str(&req.data);
    
    match parsed_data {
        Ok(mut map) => {
            map.remove("name"); // Remove name to store only unstructured properties
            let properties_json = serde_json::to_string(&map).unwrap();
            
            let conn = state.conn.lock().unwrap();
            let result = conn.execute(
                "INSERT OR REPLACE INTO products (name, properties) VALUES (?1, ?2)",
                params![req.name, properties_json],
            );
            
            if result.is_ok() {
                HttpResponse::Ok().finish()
            } else {
                HttpResponse::BadRequest().finish()
            }
        }
        Err(_) => HttpResponse::BadRequest().finish(),
    }
}

#[get("/search")]
async fn search_products(state: web::Data<Arc<DbState>>, query: web::Query<HashMap<String, String>>) -> impl Responder {
    let search_term = match query.get("query") {
        Some(q) => q,
        None => return HttpResponse::BadRequest().finish(),
    };

    let conn = state.conn.lock().unwrap();
    let mut stmt = conn
        .prepare("SELECT name, properties FROM products")
        .unwrap();
    
    let rows = stmt.query_map([], |row| {
        let name: String = row.get(0)?;
        let props_json: String = row.get(1)?;
        let props: HashMap<String, String> = serde_json::from_str(&props_json).unwrap_or_default();
        Ok(Product { name, properties: props })
    }).unwrap();

    let mut results = Vec::new();
    for row in rows {
        if let Ok(product) = row {
            // Match name or any property value
            let match_name = product.name.contains(search_term);
            let match_props = product.properties.values().any(|v| v.contains(search_term));
            
            if match_name || match_props {
                results.push(product);
            }
        }
    }

    HttpResponse::Ok().json(SearchResponse { results })
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();
    
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