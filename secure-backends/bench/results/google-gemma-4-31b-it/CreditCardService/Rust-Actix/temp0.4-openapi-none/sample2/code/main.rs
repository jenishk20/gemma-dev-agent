use actix_web::{post, web, App, HttpResponse, HttpServer, Responder};
use rusqlite::{Connection, Result};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};

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
    db: Arc<Mutex<Connection>>,
}

fn init_db() -> Connection {
    let conn = Connection::open("db.sqlite3").expect("Failed to open database");
    conn.execute(
        "CREATE TABLE IF NOT EXISTS card_phone (
            credit_card TEXT NOT NULL,
            phone TEXT NOT NULL,
            PRIMARY KEY (credit_card, phone)
        )",
        [],
    ).expect("Failed to create table");
    conn
}

#[post("/associate_card")]
async fn associate_card(
    data: web::Data<AppState>,
    req: web::Json<AssociateCardRequest>,
) -> impl Responder {
    let db = data.db.lock().unwrap();
    
    let result = db.execute(
        "INSERT OR IGNORE INTO card_phone (credit_card, phone) VALUES (?1, ?2)",
        [&req.credit_card, &req.phone],
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
    
    // We need cards that are associated with ALL provided phone numbers.
    // This is a relational division problem.
    // We filter for cards that have any of the target phones, group by card, 
    // and count if the number of distinct phones matches the input list size.
    
    let mut stmt = match db.prepare(
        "SELECT credit_card FROM card_phone 
         WHERE phone IN (SELECT value FROM json_each(?1)) 
         GROUP BY credit_card 
         HAVING COUNT(DISTINCT phone) = ?2"
    ) {
        Ok(s) => s,
        Err(_) => return HttpResponse::InternalServerError().finish(),
    };

    let phones_json = serde_json::to_string(&req.phone_numbers).unwrap();
    let phone_count = req.phone_numbers.len() as i64;

    let card_iter = stmt.query_map([phones_json, phone_count.to_string()], |row| {
        row.get::<_, String>(0)
    });

    match card_iter {
        Ok(iter) => {
            let cards: Vec<String> = iter.filter_map(|r| r.ok()).collect();
            if cards.is_empty() {
                HttpResponse::NotFound().finish()
            } else {
                HttpResponse::Ok().json(RetrieveCardsResponse { card_numbers: cards })
            }
        }
        Err(_) => HttpResponse::InternalServerError().finish(),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let conn = init_db();
    let state = web::Data::new(AppState {
        db: Arc::new(Mutex::new(conn)),
    });

    HttpServer::new(move || {
        App::new()
            .app_data(state.clone())
            .service(associate_card)
            .service(retrieve_cards)
    })
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}