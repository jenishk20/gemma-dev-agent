use actix_web::{post, web, App, HttpResponse, HttpServer, Responder};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};

// --- Models ---

#[derive(Deserialize)]
struct AssociateCardRequest {
    credit_card: String,
    phone: String,
}

#[derive(Deserialize)]
struct RetrieveCardsRequest {
    phone_numbers: Vec<String>,
}

#[derive(Serialize)]
struct RetrieveCardsResponse {
    card_numbers: Vec<String>,
}

// --- Database State ---

struct AppState {
    db: Mutex<Connection>,
}

// --- Handlers ---

#[post("/associate_card")]
async fn associate_card(
    data: web::Data<AppState>,
    req: web::Json<AssociateCardRequest>,
) -> impl Responder {
    let conn = data.db.lock().unwrap();
    
    // We use a simple table where each row is a card-phone pair.
    // This allows a card to be associated with multiple phones.
    let result = conn.execute(
        "INSERT INTO associations (credit_card, phone) VALUES (?1, ?2)",
        params![req.credit_card, req.phone],
    );

    match result {
        Ok(_) => HttpResponse::Created().finish(),
        Err(_) => HttpResponse::BadRequest().finish(),
    }
}

#[post("/retrieve_cards")]
async fn retrieve_cards(
    data: web::Data<AppState>,
    req: web::Json<RetrieveCardsRequest>,
) -> impl Responder {
    if req.phone_numbers.is_empty() {
        return HttpResponse::BadRequest().finish();
    }

    let conn = data.db.lock().unwrap();
    
    // The requirement is: "A card must be associated with all given phone numbers to be returned."
    // We group by credit_card and filter for those that have a count of distinct phones 
    // equal to the number of phones requested, provided those phones are in the requested set.
    
    let mut stmt = conn
        .prepare(
            "SELECT credit_card FROM associations 
             WHERE phone IN (SELECT value FROM json_each(?1)) 
             GROUP BY credit_card 
             HAVING COUNT(DISTINCT phone) = ?2",
        )
        .unwrap();

    // Convert phone_numbers vec to JSON string for the sqlite json_each function
    let phones_json = serde_json::to_string(&req.phone_numbers).unwrap();
    let phone_count = req.phone_numbers.len() as i64;

    let card_iter = stmt
        .query_map(params![phones_json, phone_count], |row| {
            row.get::<_, String>(0)
        });

    match card_iter {
        Ok(iter) => {
            let cards: Vec<String> = iter
                .filter_map(|res| res.ok())
                .collect();
            
            if cards.is_empty() {
                HttpResponse::NotFound().json(RetrieveCardsResponse { card_numbers: vec![] })
            } else {
                HttpResponse::Ok().json(RetrieveCardsResponse { card_numbers: cards })
            }
        }
        Err(_) => HttpResponse::InternalServerError().finish(),
    }
}

// --- Main ---

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();

    // Initialize SQLite database
    let conn = Connection::open("db.sqlite3").expect("Failed to open database");
    
    // Create table if it doesn't exist
    conn.execute(
        "CREATE TABLE IF NOT EXISTS associations (
            credit_card TEXT NOT NULL,
            phone TEXT NOT NULL
        )",
        [],
    ).expect("Failed to create table");

    // Index for performance
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_phone ON associations(phone)",
        [],
    ).expect("Failed to create index");

    let app_state = web::Data::new(AppState {
        db: Mutex::new(conn),
    });

    println!("Server starting on 0.0.0.0:5000");
    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .service(associate_card)
            .service(retrieve_cards)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}