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
    let cart_id = Uuid::new_v4().to_string();
    let db = data.db.lock().unwrap();

    // Create the cart by initializing it in the items table or a separate carts table.
    // For this simple implementation, we'll just ensure the ID is tracked.
    // We use a separate table 'carts' to track existence.
    let res = db.execute("INSERT INTO carts (id) VALUES (?1)", params![cart_id]);

    match res {
        Ok(_) => HttpResponse::Created().json(CreateCartResponse { cart_id }),
        Err(_) => HttpResponse::InternalServerError().finish(),
    }
}

#[post("/add_to_cart")]
async fn add_to_cart(data: web::Data<AppState>, req: web::Json<AddToCartRequest>) -> impl Responder {
    let db = data.db.lock().unwrap();

    // Check if cart exists
    let exists: bool = db
        .query_row("SELECT EXISTS(SELECT 1 FROM carts WHERE id = ?1)", params![req.cart_id], |_| Ok(true))
        .unwrap_or(false);

    if !exists {
        return HttpResponse::NotFound().body("Cart not found");
    }

    // Upsert item count
    let res = db.execute(
        "INSERT INTO cart_items (cart_id, item_id, count) 
         VALUES (?1, ?2, ?3) 
         ON CONFLICT(cart_id, item_id) 
         DO UPDATE SET count = count + excluded.count",
        params![req.cart_id, req.item_id, req.count],
    );

    match res {
        Ok(_) => {
            // Optional: Remove items with count <= 0
            let _ = db.execute("DELETE FROM cart_items WHERE count <= 0", []);
            HttpResponse::Ok().finish()
        }
        Err(_) => HttpResponse::InternalServerError().finish(),
    }
}

#[post("/retrieve_cart")]
async fn retrieve_cart(data: web::Data<AppState>, req: web::Json<RetrieveCartRequest>) -> impl Responder {
    let db = data.db.lock().unwrap();

    // Check if cart exists
    let exists: bool = db
        .query_row("SELECT EXISTS(SELECT 1 FROM carts WHERE id = ?1)", params![req.cart_id], |_| Ok(true))
        .unwrap_or(false);

    if !exists {
        return HttpResponse::NotFound().body("Cart not found");
    }

    let mut stmt = db
        .prepare("SELECT item_id, count FROM cart_items WHERE cart_id = ?1")
        .unwrap();

    let items_iter = stmt
        .query_map(params![req.cart_id], |row| {
            Ok(CartItem {
                item_id: row.get(0)?,
                count: row.get(1)?,
            })
        })
        .unwrap();

    let mut items = Vec::new();
    for item in items_iter {
        if let Ok(i) = item {
            items.push(i);
        }
    }

    HttpResponse::Ok().json(RetrieveCartResponse { items })
}

// --- Main ---

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // Initialize Database
    let conn = Connection::open("db.sqlite3").expect("Failed to open database");
    
    conn.execute(
        "CREATE TABLE IF NOT EXISTS carts (id TEXT PRIMARY KEY)",
        [],
    ).expect("Failed to create carts table");

    conn.execute(
        "CREATE TABLE IF NOT EXISTS cart_items (
            cart_id TEXT, 
            item_id INTEGER, 
            count INTEGER, 
            PRIMARY KEY (cart_id, item_id),
            FOREIGN KEY(cart_id) REFERENCES carts(id)
        )",
        [],
    ).expect("Failed to create cart_items table");

    let app_state = web::Data::new(AppState {
        db: Mutex::new(conn),
    });

    println!("Starting server on 0.0.0.0:5000");
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