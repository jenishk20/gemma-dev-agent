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
    let db = data.db.lock().unwrap();
    
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
async fn retrieve_cards(data: web::Data<AppState>, req: web::Json<RetrieveRequest>) -> impl Responder {
    if req.phone_numbers.is_empty() {
        return HttpResponse::BadRequest().finish();
    }

    let db = data.db.lock().unwrap();
    
    // The requirement is: "A card must be associated with all given phone numbers to be returned."
    // We group by credit_card and filter for those that have a count of distinct phones equal to the input list size,
    // provided those phones are in the input list.
    
    let mut stmt = db
        .prepare(
            "SELECT credit_card FROM associations 
             WHERE phone IN (SELECT value FROM pragma_table_info('associations')) 
             AND phone IN (SELECT value FROM json_each(?1))
             GROUP BY credit_card 
             HAVING COUNT(DISTINCT phone) = ?2",
        )
        .unwrap_or_else(|_| {
            // Fallback for simpler SQL if json_each is problematic in specific sqlite versions, 
            // though modern-full usually supports it.
            db.prepare("SELECT credit_card FROM associations WHERE phone = ?1 GROUP BY credit_card").unwrap()
        });

    // Since rusqlite doesn't easily map Vec to IN clauses without a helper, 
    // we build the query dynamically or use a temporary table. 
    // For simplicity and correctness with the provided constraints:
    
    let phones = &req.phone_numbers;
    let phone_count = phones.len() as i64;
    
    // Constructing a query like: SELECT credit_card FROM associations WHERE phone IN ('p1', 'p2') GROUP BY credit_card HAVING COUNT(DISTINCT phone) = 2
    let placeholders = phones.iter().map(|_| "?").collect::<Vec<_>>().join(",");
    let query = format!(
        "SELECT credit_card FROM associations WHERE phone IN ({}) GROUP BY credit_card HAVING COUNT(DISTINCT phone) = ?",
        placeholders
    );

    let mut params_vec: Vec<rusqlite::types::Value> = phones
        .iter()
        .map(|p| rusqlite::types::Value::Text(p.clone()))
        .collect();
    params_vec.push(rusqlite::types::Value::Integer(phone_count));

    let mut stmt = match db.prepare_cached(&query) {
        Ok(s) => s,
        Err(_) => return HttpResponse::InternalServerError().finish(),
    };

    let card_iter = stmt.query_map(rusqlite::params_from_iter(params_vec), |row| {
        row.get::<_, String>(0)
    });

    match card_iter {
        Ok(iter) => {
            let cards: Vec<String> = iter.filter_map(|r| r.ok()).collect();
            if cards.is_empty() {
                HttpResponse::NotFound().finish()
            } else {
                HttpResponse::Ok().json(RetrieveResponse { card_numbers: cards })
            }
        }
        Err(_) => HttpResponse::InternalServerError().finish(),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let conn = Connection::open("db.sqlite3").expect("Failed to open database");
    
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