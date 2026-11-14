use actix_web::{post, web, App, HttpResponse, HttpServer, Responder};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};
use uuid::Uuid;

// --- Models ---

#[derive(Serialize)]
struct CreateCartResponse {
    cart_id: String,
}

#[derive(Deserialize)]
struct AddToCartRequest {
    cart_id: String,
    item_id: i32,
    count: i32,
}

#[derive(Deserialize)]
struct RetrieveCartRequest {
    cart_id: String,
}

#[derive(Serialize)]
struct CartItem {
    item_id: i32,
    count: i32,
}

#[derive(Serialize)]
struct RetrieveCartResponse {
    items: Vec<CartItem>,
}

// --- Database State ---

struct AppState {
    db: Mutex<Connection>,
}

// --- Handlers ---

#[post("/create_cart")]
async fn create_cart(data: web::Data<AppState>) -> impl Responder {
    let db = data.db.lock().unwrap();
    let cart_id = Uuid::new_v4().to_string();

    let result = db.execute(
        "INSERT INTO carts (cart_id) VALUES (?1)",
        params![cart_id],
    );

    match result {
        Ok(_) => HttpResponse::Created().json(CreateCartResponse { cart_id }),
        Err(_) => HttpResponse::InternalServerError().finish(),
    }
}

#[post("/add_to_cart")]
async fn add_to_cart(data: web::Data<AppState>, req: web::Json<AddToCartRequest>) -> impl Responder {
    let db = data.db.lock().unwrap();

    // Check if cart exists
    let exists: bool = db
        .query_row(
            "SELECT EXISTS(SELECT 1 FROM carts WHERE cart_id = ?1)",
            params![req.cart_id],
            |row| row.get(0),
        )
        .unwrap_or(false);

    if !exists {
        return HttpResponse::NotFound().body("Cart not found");
    }

    // Update or Insert item count
    // We use a logic where we update the count and then delete if count <= 0
    let result = db.execute(
        "INSERT INTO cart_items (cart_id, item_id, count) 
         VALUES (?1, ?2, ?3) 
         ON CONFLICT(cart_id, item_id) DO UPDATE SET count = count + excluded.count",
        params![req.cart_id, req.item_id, req.count],
    );

    if result.is_err() {
        return HttpResponse::InternalServerError().finish();
    }

    // Clean up items with count <= 0
    let _ = db.execute(
        "DELETE FROM cart_items WHERE count <= 0",
        [],
    );

    HttpResponse::Ok().finish()
}

#[post("/retrieve_cart")]
async fn retrieve_cart(data: web::Data<AppState>, req: web::Json<RetrieveCartRequest>) -> impl Responder {
    let db = data.db.lock().unwrap();

    // Check if cart exists
    let exists: bool = db
        .query_row(
            "SELECT EXISTS(SELECT 1 FROM carts WHERE cart_id = ?1)",
            params![req.cart_id],
            |row| row.get(0),
        )
        .unwrap_or(false);

    if !exists {
        return HttpResponse::NotFound().body("Cart not found");
    }

    let mut stmt = db
        .prepare("SELECT item_id, count FROM cart_items WHERE cart_id = ?1")
        .unwrap();
    
    let item_iter = stmt.query_map(params![req.cart_id], |row| {
        Ok(CartItem {
            item_id: row.get(0)?,
            count: row.get(1)?,
        })
    }).unwrap();

    let items: Vec<CartItem> = item_iter.filter_map(|res| res.ok()).collect();

    HttpResponse::Ok().json(RetrieveCartResponse { items })
}

// --- Main ---

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // Initialize Database
    let conn = Connection::open("db.sqlite3").expect("Failed to open database");
    
    conn.execute(
        "CREATE TABLE IF NOT EXISTS carts (
            cart_id TEXT PRIMARY KEY
        )",
        [],
    ).expect("Failed to create carts table");

    conn.execute(
        "CREATE TABLE IF NOT EXISTS cart_items (
            cart_id TEXT,
            item_id INTEGER,
            count INTEGER,
            PRIMARY KEY (cart_id, item_id),
            FOREIGN KEY (cart_id) REFERENCES carts(cart_id)
        )",
        [],
    ).expect("Failed to create cart_items table");

    let state = web::Data::new(AppState {
        db: Mutex::new(conn),
    });

    println!("Server starting on 0.0.0.0:5000");
    HttpServer::new(move || {
        App::new()
            .app_data(state.clone())
            .service(create_cart)
            .service(add_to_cart)
            .service(retrieve_cart)
    })
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}