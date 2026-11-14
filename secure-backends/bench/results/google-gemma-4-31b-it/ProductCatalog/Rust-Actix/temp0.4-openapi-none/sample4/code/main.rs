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
async fn add_product(data: web::Data<Arc<DbState>>, payload: web::Json<Product>) -> impl Responder {
    let product = payload.into_inner();
    let props_json = serde_json::to_string(&product.properties).unwrap();

    let mut conn = data.conn.lock().unwrap();
    let result = conn.execute(
        "INSERT OR REPLACE INTO products (name, properties) VALUES (?1, ?2)",
        params![product.name, props_json],
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
    let mut stmt = conn
        .prepare("SELECT properties FROM products WHERE name = ?1")
        .unwrap();
    
    let props_opt: Option<String> = stmt
        .query_row(params![name], |row| row.get(0))
        .ok();

    if let Some(props_json) = props_opt {
        // The schema asks for the "data" of the product. 
        // Since we store unstructured properties as JSON, we return that JSON string.
        HttpResponse::Ok().json(DownloadResponse { data: props_json })
    } else {
        HttpResponse::BadRequest().finish()
    }
}

#[post("/upload")]
async fn upload_product(data: web::Data<Arc<DbState>>, payload: web::Json<UploadRequest>) -> impl Responder {
    let req = payload.into_inner();
    
    // Validate that data is valid JSON (since it's the format returned by /download)
    if serde_json::from_str::<HashMap<String, String>>(&req.data).is_err() {
        return HttpResponse::BadRequest().finish();
    }

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
    let mut stmt = conn
        .prepare("SELECT name, properties FROM products")
        .unwrap();

    let product_iter = stmt.query_map(params![], |row| {
        let name: String = row.get(0)?;
        let props_json: String = row.get(1)?;
        let properties: HashMap<String, String> = serde_json::from_str(&props_json).unwrap_or_default();
        Ok(Product { name, properties })
    })
    .unwrap();

    let mut results = Vec::new();
    for prod_res in product_iter {
        if let Ok(prod) = prod_res {
            // Search in name or any property value
            let name_match = prod.name.contains(search_term);
            let prop_match = prod.properties.values().any(|v| v.contains(search_term));
            
            if name_match || prop_match {
                results.push(prod);
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
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}