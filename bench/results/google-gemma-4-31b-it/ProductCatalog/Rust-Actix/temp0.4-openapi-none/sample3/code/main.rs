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

#[derive(Deserialize)]
struct DownloadQuery {
    name: String,
}

#[derive(Deserialize)]
struct SearchQuery {
    query: String,
}

#[derive(Serialize, Deserialize)]
struct DownloadResponse {
    data: String,
}

#[derive(Serialize, Deserialize)]
struct UploadRequest {
    name: String,
    data: String,
}

#[derive(Serialize)]
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
    let props_json = serde_json::to_string(&product.properties).unwrap();

    let conn = state.conn.lock().unwrap();
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
async fn download_product(state: web::Data<Arc<DbState>>, query: web::Query<DownloadQuery>) -> impl Responder {
    let conn = state.conn.lock().unwrap();
    let mut stmt = conn
        .prepare("SELECT properties FROM products WHERE name = ?1")
        .unwrap();
    
    let product_props: Result<String, _> = stmt.query_row(params![query.name], |row| row.get(0));

    match product_props {
        Ok(props) => {
            // The schema implies the "data" is a string representation of the product's unstructured properties
            HttpResponse::Ok().json(DownloadResponse { data: props })
        }
        Err(_) => HttpResponse::NotFound().finish(),
    }
}

#[post("/upload")]
async fn upload_product(state: web::Data<Arc<DbState>>, req: web::Json<UploadRequest>) -> impl Responder {
    let req = req.into_inner();
    
    // Validate that the data is valid JSON (since it's stored as JSON string)
    if serde_json::from_str::<HashMap<String, String>>(&req.data).is_err() {
        return HttpResponse::BadRequest().finish();
    }

    let conn = state.conn.lock().unwrap();
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
async fn search_products(state: web::Data<Arc<DbState>>, query: web::Query<SearchQuery>) -> impl Responder {
    let conn = state.conn.lock().unwrap();
    let mut stmt = conn
        .prepare("SELECT name, properties FROM products")
        .unwrap();

    let rows = stmt.query_map(params! [], |row| {
        let name: String = row.get(0)?;
        let props_str: String = row.get(1)?;
        let properties: HashMap<String, String> = serde_json::from_str(&props_str).unwrap_or_default();
        Ok((name, properties))
    }).unwrap();

    let mut results = Vec::new();
    let search_term = query.query.to_lowercase();

    for row in rows {
        if let Ok((name, props)) = row {
            let name_match = name.to_lowercase().contains(&search_term);
            let props_match = props.iter().any(|(k, v)| {
                k.to_lowercase().contains(&search_term) || v.to_lowercase().contains(&search_term)
            });

            if name_match || props_match {
                let mut product = Product {
                    name,
                    properties: props,
                };
                // The Product struct uses flatten, so we need to merge properties into the map
                // but since Product is defined as name + HashMap, we just construct it.
                results.push(product);
            }
        }
    }

    // To satisfy the "additionalProperties" in the response, we need to map the Product 
    // back to a JSON object where 'name' is a key and others are flat.
    // Since our Product struct already does this via #[serde(flatten)], we can just return it.
    
    // Re-constructing the results to ensure they match the expected OpenAPI output format
    let final_results: Vec<serde_json::Value> = results.into_iter().map(|p| {
        let mut map = serde_json::Map::new();
        map.insert("name".to_string(), serde_json::Value::String(p.name));
        for (k, v) in p.properties {
            map.insert(k, serde_json::Value::String(v));
        }
        serde_json::Value::Object(map)
    }).collect();

    HttpResponse::Ok().json(serde_json::json!( { "results": final_results } ))
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