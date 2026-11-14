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

struct AppState {
    db: Mutex<Connection>,
}

// --- Handlers ---

#[post("/associate_card")]
async fn associate_card(
    data: web::Data<AppState>,
    req: web::Json<AssociateCardRequest>,
) -> impl Responder {
    let db = data.db.lock().unwrap();
    
    // Insert the association. We use IGNORE or a check to avoid duplicates if necessary, 
    // but the schema implies a simple association.
    let result = db.execute(
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

    let db = data.db.lock().unwrap();
    
    // To find cards associated with ALL given phone numbers:
    // We select cards that have a match for the phone, group by card, 
    // and filter for groups where the count of distinct phones matches the input list size.
    let mut query = String::from("SELECT credit_card FROM associations WHERE phone IN (");
    for (i, phone) in req.phone_numbers.iter().enumerate() {
        query.push('\'');
        query.push_str(phone);
        query.push('\'');
        if i < req.phone_numbers.len() - 1 {
            query.push_str(", ");
        }
    }
    query.push_str(") GROUP BY credit_card HAVING COUNT(DISTINCT phone) = ?");

    let mut stmt = match db.prepare(&query) {
        Ok(s) => s,
        Err(_) => return HttpResponse::InternalServerError().finish(),
    };

    let card_iter = stmt.query_map(params![req.phone_numbers.len()], |row| {
        row.get::<_, String>(0)
    });

    match card_iter {
        Ok(iter) => {
            let cards: Vec<String> = iter.filter_map(|r| r.ok()).collect();
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
    // Initialize Database
    let conn = Connection::open("db.sqlite3").expect("Failed to open database");
    
    conn.execute(
        "CREATE TABLE IF NOT EXISTS associations (
            credit_card TEXT NOT NULL,
            phone TEXT NOT NULL
        )",
        [],
    ).expect("Failed to create table");

    // Index for performance on retrieval
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
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}