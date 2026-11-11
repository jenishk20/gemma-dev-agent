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
    item_id: i64,
    count: i64,
}

#[derive(Deserialize)]
struct RetrieveCartRequest {
    cart_id: String,
}

#[derive(Serialize)]
struct CartItem {
    item_id: i64,
    count: i64,
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
    let mut conn = data.db.lock().unwrap();
    let cart_id = Uuid::new_v4().to_string();

    // Create a cart entry. We use a simple table structure where the cart_id is the primary key.
    // The items are stored in a separate table.
    let result = conn.execute(
        "INSERT INTO carts (id) VALUES (?)",
        params![cart_id],
    );

    match result {
        Ok(_) => HttpResponse::Created().json(CreateCartResponse { cart_id }),
        Err(_) => HttpResponse::InternalServerError().finish(),
    }
}

#[post("/add_to_cart")]
async fn add_to_cart(data: web::Data<AppState>, req: web::Json<AddToCartRequest>) -> impl Responder {
    let mut conn = data.db.lock().unwrap();

    // Check if cart exists
    let exists: bool = conn
        .query_row(
            "SELECT EXISTS(SELECT 1 FROM carts WHERE id = ?)",
            params![req.cart_id],
            |row| row.get(0),
        )
        .unwrap_or(false);

    if !exists {
        return HttpResponse::NotFound().finish();
    }

    // Upsert logic for items in the cart
    // If item exists, update count. If not, insert.
    let result = conn.execute(
        "INSERT INTO cart_items (cart_id, item_id, count) 
         VALUES (?, ?, ?) 
         ON CONFLICT(cart_id, item_id) DO UPDATE SET count = count + excluded.count",
        params![req.cart_id, req.item_id, req.count],
    );

    match result {
        Ok(_) => {
            // Remove item if count drops to 0 or less
            let _ = conn.execute(
                "DELETE FROM cart_items WHERE count <= 0",
                [],
            );
            HttpResponse::Ok().finish()
        }
        Err(_) => HttpResponse::InternalServerError().finish(),
    }
}

#[post("/retrieve_cart")]
async fn retrieve_cart(data: web::Data<AppState>, req: web::Json<RetrieveCartRequest>) -> impl Responder {
    let conn = data.db.lock().unwrap();

    // Check if cart exists
    let exists: bool = conn
        .query_row(
            "SELECT EXISTS(SELECT 1 FROM carts WHERE id = ?)",
            params![req.cart_id],
            |row| row.get(0),
        )
        .unwrap_or(false);

    if !exists {
        return HttpResponse::NotFound().finish();
    }

    let mut stmt = conn
        .prepare("SELECT item_id, count FROM cart_items WHERE cart_id = ?")
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
    // Initialize SQLite database
    let conn = Connection::open("db.sqlite3").expect("Failed to open database");

    conn.execute(
        "CREATE TABLE IF NOT EXISTS carts (
            id TEXT PRIMARY KEY
        )",
        [],
    ).expect("Failed to create carts table");

    conn.execute(
        "CREATE TABLE IF NOT EXISTS cart_items (
            cart_id TEXT,
            item_id INTEGER,
            count INTEGER,
            PRIMARY KEY (cart_id, item_id),
            FOREIGN KEY (cart_id) REFERENCES carts(id)
        )",
        [],
    ).expect("Failed to create cart_items table");

    let app_state = web::Data::new(AppState {
        db: Mutex::new(conn),
    });

    println!("Starting server at http://0.0.0.0:5000");
    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .service(create_cart)
            .service(add_to_cart)
            .service(retrieve_cart)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}