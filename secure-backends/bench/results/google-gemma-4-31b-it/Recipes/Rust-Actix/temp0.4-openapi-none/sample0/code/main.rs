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
struct CommentRequest {
    comment: String,
}

#[derive(Deserialize)]
struct RatingRequest {
    rating: i32,
}

// --- Database Manager ---

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
            recipe_id TEXT NOT NULL,
            comment TEXT NOT NULL,
            FOREIGN KEY(recipe_id) REFERENCES recipes(id)
        )",
        [],
    ).expect("Failed to create comments table");

    conn.execute(
        "CREATE TABLE IF NOT EXISTS ratings (
            recipe_id TEXT NOT NULL,
            rating INTEGER NOT NULL,
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

    let mut html = String::from("<h1>Recipe Overview</h1><ul>");
    for row in rows {
        if let Ok((id, title)) = row {
            html.push_str(&format!("<li><a href='/recipes/{}'>{}</a></li>", id, title));
        }
    }
    html.push_str("</ul>");

    HttpResponse::Ok().content_type("text/html").body(html)
}

#[post("/recipes/upload")]
async fn upload_recipe(data: web::Data<Arc<DbState>>, payload: web::Json<UploadRecipeRequest>) -> impl Responder {
    let conn = data.conn.lock().unwrap();
    let id = Uuid::new_v4().to_string();
    let ingredients_json = serde_json::to_string(&payload.ingredients).unwrap();

    let res = conn.execute(
        "INSERT INTO recipes (id, title, ingredients, instructions) VALUES (?1, ?2, ?3, ?4)",
        params![id, payload.title, ingredients_json, payload.instructions],
    );

    match res {
        Ok(_) => {
            let recipe = Recipe {
                id,
                title: payload.title.clone(),
                ingredients: payload.ingredients.clone(),
                instructions: payload.instructions.clone(),
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

    let recipe_res = conn.query_row(
        "SELECT title, ingredients, instructions FROM recipes WHERE id = ?1",
        params![recipe_id],
        |row| {
            let ing_str: String = row.get(1)?;
            let ingredients: Vec<String> = serde_json::from_str(&ing_str).unwrap_or_default();
            Ok((row.get::<_, String>(0)?, ingredients, row.get::<_, String>(2)?))
        },
    );

    if let Err(_) = recipe_res {
        return HttpResponse::NotFound().finish();
    }
    let (title, ingredients, instructions) = recipe_res.unwrap();

    let mut stmt_comm = conn.prepare("SELECT comment FROM comments WHERE recipe_id = ?1").unwrap();
    let comments_iter = stmt_comm.query_map(params![recipe_id], |row| {
        Ok(Comment { comment: row.get(0)? })
    }).unwrap();
    let comments: Vec<Comment> = comments_iter.filter_map(|r| r.ok()).collect();

    let avg_rating: Option<f64> = conn.query_row(
        "SELECT AVG(rating) FROM ratings WHERE recipe_id = ?1",
        params![recipe_id],
        |row| row.get(0),
    ).unwrap_or(None);

    let mut html = format!("<h1>{}</h1>", title);
    html.push_str(&format!("<p><strong>Ingredients:</strong> {}</p>", ingredients.join(", ")));
    html.push_str(&format!("<p><strong>Instructions:</strong> {}</p>", instructions));
    html.push_str(&format!("<p><strong>Average Rating:</strong> {:?}</p>", avg_rating));
    html.push_str("<h3>Comments</h3><ul>");
    for c in comments {
        html.push_str(&format!("<li>{}</li>", c.comment));
    }
    html.push_str("</ul><br><a href='/recipes'>Back to overview</a>");

    HttpResponse::Ok().content_type("text/html").body(html)
}

#[post("/recipes/{recipeId}/comments")]
async fn add_comment(data: web::Data<Arc<DbState>>, path: web::Path<String>, payload: web::Json<CommentRequest>) -> impl Responder {
    let recipe_id = path.into_inner();
    let conn = data.conn.lock().unwrap();

    let exists: bool = conn.query_row("SELECT EXISTS(SELECT 1 FROM recipes WHERE id = ?1)", params![recipe_id], |row| row.get(0)).unwrap_or(false);
    if !exists {
        return HttpResponse::NotFound().finish();
    }

    match conn.execute("INSERT INTO comments (recipe_id, comment) VALUES (?1, ?2)", params![recipe_id, payload.comment]) {
        Ok(_) => HttpResponse::Created().finish(),
        Err(_) => HttpResponse::BadRequest().finish(),
    }
}

#[post("/recipes/{recipeId}/ratings")]
async fn add_rating(data: web::Data<Arc<DbState>>, path: web::Path<String>, payload: web::Json<RatingRequest>) -> impl Responder {
    let recipe_id = path.into_inner();
    let conn = data.conn.lock().unwrap();

    if payload.rating < 1 || payload.rating > 5 {
        return HttpResponse::BadRequest().finish();
    }

    let exists: bool = conn.query_row("SELECT EXISTS(SELECT 1 FROM recipes WHERE id = ?1)", params![recipe_id], |row| row.get(0)).unwrap_or(false);
    if !exists {
        return HttpResponse::NotFound().finish();
    }

    match conn.execute("INSERT INTO ratings (recipe_id, rating) VALUES (?1, ?2)", params![recipe_id, payload.rating]) {
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