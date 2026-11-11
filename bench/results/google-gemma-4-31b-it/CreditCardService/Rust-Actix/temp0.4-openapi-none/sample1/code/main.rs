use actix_web::{post, web, App, HttpResponse, HttpServer, Responder};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};

#[derive(Deserialize)]
struct AssociateRequest {
    credit_card: String,
    phone: String,
}

#[derive(Deserialize)]
struct RetrieveRequest {
    phone_numbers: Vec<String>,
}

#[derive(Serialize)]
struct RetrieveResponse {
    card_numbers: Vec<String>,
}

struct AppState {
    db: Mutex<Connection>,
}

#[post("/associate_card")]
async fn associate_card(data: web::Data<AppState>, req: web::Json<AssociateRequest>) -> impl Responder {
    let conn = data.db.lock().unwrap();
    
    let res = conn.execute(
        "INSERT INTO associations (credit_card, phone) VALUES (?1, ?2)",
        params![req.credit_card, req.phone],
    );

    match res {
        Ok(_) => HttpResponse::Created().finish(),
        Err(_) => HttpResponse::BadRequest().finish(),
    }
}

#[post("/retrieve_cards")]
async fn retrieve_cards(data: web::Data<AppState>, req: web::Json<RetrieveRequest>) -> impl Responder {
    if req.phone_numbers.is_empty() {
        return HttpResponse::BadRequest().finish();
    }

    let conn = data.db.lock().unwrap();
    
    // We need to find cards that are associated with ALL provided phone numbers.
    // We group by credit_card and count how many of the requested phones match.
    // If the count equals the number of requested phones, the card is associated with all of them.
    let mut stmt = conn
        .prepare(
            "SELECT credit_card FROM associations 
             WHERE phone IN (SELECT value FROM json_each(?1)) 
             GROUP BY credit_card 
             HAVING COUNT(DISTINCT phone) = ?2",
        )
        .unwrap();

    let phones_json = serde_json::to_string(&req.phone_numbers).unwrap();
    let card_iter = stmt
        .query_map(params![phones_json, req.phone_numbers.len()], |row| {
            row.get::<_, String>(0)
        });

    match card_iter {
        Ok(iter) => {
            let cards: Vec<String> = iter.filter_map(|c| c.ok()).collect();
            if cards.is_empty() {
                HttpResponse::NotFound().finish()
            } else {
                HttpResponse::Ok().json(RetrieveResponse {
                    card_numbers: cards,
                })
            }
        }
        Err(_) => HttpResponse::InternalServerError().finish(),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // Initialize SQLite database
    let conn = Connection::open("db.sqlite3").expect("Failed to open database");
    
    conn.execute(
        "CREATE TABLE IF NOT EXISTS associations (
            id INTEGER PRIMARY KEY,
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

    println!("Starting server at http://0.0.0.0:5000");
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