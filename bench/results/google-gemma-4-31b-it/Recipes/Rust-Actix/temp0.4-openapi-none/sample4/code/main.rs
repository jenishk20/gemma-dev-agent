use actix_web::{get, post, web, App, HttpResponse, HttpServer, Responder};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};
use uuid::Uuid;

// --- Models ---

#[derive(Serialize, Deserialize, Clone)]
struct Recipe {
    id: String,
    title: String,
    ingredients: Vec<String>,
    instructions: String,
    comments: Vec<Comment>,
    #[serde(rename = "avgRating")]
    avg_rating: Option<f64>,
}

#[derive(Serialize, Deserialize, Clone)]
struct Comment {
    comment: String,
}

#[derive(Deserialize)]
struct UploadRecipeRequest {
    title: String,
    ingredients: Vec<String>,
    instructions: String,
}

#[derive(Deserialize)]
struct AddCommentRequest {
    comment: String,
}

#[derive(Deserialize)]
struct AddRatingRequest {
    rating: i32,
}

// --- Database Management ---

struct DbState {
    conn: Mutex<Connection>,
}

fn init_db() -> Connection {
    let conn = Connection::open("db.sqlite3").expect("Failed to open database");
    conn.execute(
        "CREATE TABLE IF NOT EXISTS recipes (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            ingredients TEXT NOT NULL,
            instructions TEXT NOT NULL
        )",
        [],
    ).expect("Failed to create recipes table");

    conn.execute(
        "CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipe_id TEXT NOT NULL,
            content TEXT NOT NULL,
            FOREIGN KEY(recipe_id) REFERENCES recipes(id)
        )",
        [],
    ).expect("Failed to create comments table");

    conn.execute(
        "CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipe_id TEXT NOT NULL,
            score INTEGER NOT NULL,
            FOREIGN KEY(recipe_id) REFERENCES recipes(id)
        )",
        [],
    ).expect("Failed to create ratings table");

    conn
}

// --- Handlers ---

#[get("/recipes")]
async fn get_recipes_overview(data: web::Data<Arc<DbState>>) -> impl Responder {
    let conn = data.conn.lock().unwrap();
    let mut stmt = conn
        .prepare("SELECT id, title FROM recipes LIMIT 20")
        .unwrap();
    
    let rows = stmt.query_map([], |row| {
        Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
    }).unwrap();

    let mut html = String::from("<html><body><h1>Recipe Overview</h1><ul>");
    for row in rows {
        if let Ok((id, title)) = row {
            html.push_str(&format!("<li><a href='/recipes/{}'>{}</a></li>", id, title));
        }
    }
    html.push_str("</ul></body></html>");

    HttpResponse::Ok().content_type("text/html").body(html)
}

#[post("/recipes/upload")]
async fn upload_recipe(data: web::Data<Arc<DbState>>, req: web::Json<UploadRecipeRequest>) -> impl Responder {
    let conn = data.conn.lock().unwrap();
    let id = Uuid::new_v4().to_string();
    let ingredients_json = serde_json::to_string(&req.ingredients).unwrap();

    let res = conn.execute(
        "INSERT INTO recipes (id, title, ingredients, instructions) VALUES (?1, ?2, ?3, ?4)",
        params![id, req.title, ingredients_json, req.instructions],
    );

    match res {
        Ok(_) => {
            let recipe = Recipe {
                id,
                title: req.title.clone(),
                ingredients: req.ingredients.clone(),
                instructions: req.instructions.clone(),
                comments: vec![],
                avg_rating: None,
            };
            HttpResponse::Created().json(recipe)
        }
        Err(_) => HttpResponse::BadRequest().finish(),
    }
}

#[get("/recipes/{recipeId}")]
async fn get_recipe(data: web::Data<Arc<DbState>>, path: web::Path<String>) -> impl Responder {
    let recipe_id = path.into_inner();
    let conn = data.conn.lock().unwrap();

    let recipe_row = conn.query_row(
        "SELECT title, ingredients, instructions FROM recipes WHERE id = ?1",
        params![recipe_id],
        |row| {
            Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?, row.get::<_, String>(2)?))
        },
    );

    if let Err(_) = recipe_row {
        return HttpResponse::NotFound().finish();
    }

    let (title, ingredients_raw, instructions) = recipe_row.unwrap();
    let ingredients: Vec<String> = serde_json::from_str(&ingredients_raw).unwrap_or_default();

    let mut comments_stmt = conn.prepare("SELECT content FROM comments WHERE recipe_id = ?1").unwrap();
    let comments_iter = comments_stmt.query_map(params![recipe_id], |row| {
        Ok(Comment { comment: row.get(0)? })
    }).unwrap();
    let comments: Vec<Comment> = comments_iter.filter_map(|r| r.ok()).collect();

    let avg_rating: Option<f64> = conn.query_row(
        "SELECT AVG(score) FROM ratings WHERE recipe_id = ?1",
        params![recipe_id],
        |row| row.get(0),
    ).ok();

    let html = format!(
        "<html><body><h1>{}</h1><p><b>Ingredients:</b> {}</p><p><b>Instructions:</b> {}</p><p><b>Rating:</b> {:?}</p><h3>Comments</h3><ul>",
        title, ingredients.join(", "), instructions, avg_rating
    );
    let mut final_html = html;
    for c in comments {
        final_html.push_str(&format!("<li>{}</li>", c.comment));
    }
    final_html.push_str("</ul><br><a href='/recipes'>Back</a></body></html>");

    HttpResponse::Ok().content_type("text/html").body(final_html)
}

#[post("/recipes/{recipeId}/comments")]
async fn add_comment(data: web::Data<Arc<DbState>>, path: web::Path<String>, req: web::Json<AddCommentRequest>) -> impl Responder {
    let recipe_id = path.into_inner();
    let conn = data.conn.lock().unwrap();

    let exists = conn.query_row("SELECT 1 FROM recipes WHERE id = ?1", params![recipe_id], |_| Ok(())).is_ok();
    if !exists {
        return HttpResponse::NotFound().finish();
    }

    match conn.execute("INSERT INTO comments (recipe_id, content) VALUES (?1, ?2)", params![recipe_id, req.comment]) {
        Ok(_) => HttpResponse::Created().finish(),
        Err(_) => HttpResponse::BadRequest().finish(),
    }
}

#[post("/recipes/{recipeId}/ratings")]
async fn add_rating(data: web::Data<Arc<DbState>>, path: web::Path<String>, req: web::Json<AddRatingRequest>) -> impl Responder {
    let recipe_id = path.into_inner();
    let conn = data.conn.lock().unwrap();

    if req.rating < 1 || req.rating > 5 {
        return HttpResponse::BadRequest().finish();
    }

    let exists = conn.query_row("SELECT 1 FROM recipes WHERE id = ?1", params![recipe_id], |_| Ok(())).is_ok();
    if !exists {
        return HttpResponse::NotFound().finish();
    }

    match conn.execute("INSERT INTO ratings (recipe_id, score) VALUES (?1, ?2)", params![recipe_id, req.rating]) {
        Ok(_) => HttpResponse::Created().finish(),
        Err(_) => HttpResponse::BadRequest().finish(),
    }
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
            .service(get_recipes_overview)
            .service(upload_recipe)
            .service(get_recipe)
            .service(add_comment)
            .service(add_rating)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}