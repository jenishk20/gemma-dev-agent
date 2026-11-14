use actix_multipart::Multipart;
use actix_web::{post, web, App, HttpResponse, HttpServer, Responder};
use futures_util::{StreamExt, TryStreamExt};
use std::fs::File;
use std::io::Write;
use std::process::Command;
use tempdir::TempDir;
use uuid::Uuid;

#[post("/create-gif")]
async fn create_gif(mut payload: Multipart) -> impl Responder {
    let temp_dir = match TempDir::new() {
        Ok(dir) => dir,
        Err(_) => return HttpResponse::InternalServerError().json(serde_json::json!({"error": "Could not create temp directory"})),
    };

    let mut images_paths = Vec::new();
    let mut target_size = String::new();
    let mut delay = "10".to_string();
    let mut append_reverted = "false".to_string();

    // Process multipart form data
    while let Ok(Some(mut field)) = payload.try_next().await {
        let content_type = field.name().to_string();
        
        if content_type == "images" {
            let file_id = Uuid::new_v4().to_string();
            let file_path = format!("{}/{}.tmp", temp_dir.path().to_str().unwrap(), file_id);
            let mut f = File::create(&file_path).unwrap();
            
            while let Ok(Some(chunk)) = field.try_next().await {
                f.write_all(&chunk).unwrap();
            }
            images_paths.push(file_path);
        } else if content_type == "targetSize" {
            let mut bytes = Vec::new();
            while let Ok(Some(chunk)) = field.try_next().await {
                bytes.extend_from_slice(&chunk);
            }
            target_size = String::from_utf8_lossy(&bytes).to_string();
        } else if content_type == "delay" {
            let mut bytes = Vec::new();
            while let Ok(Some(chunk)) = field.try_next().await {
                bytes.extend_from_slice(&chunk);
            }
            delay = String::from_utf8_lossy(&bytes).to_string();
        } else if content_type == "appendReverted" {
            let mut bytes = Vec::new();
            while let Ok(Some(chunk)) = field.try_next().await {
                bytes.extend_from_slice(&chunk);
            }
            append_reverted = String::from_utf8_lossy(&bytes).to_string();
        }
    }

    if images_paths.is_empty() || target_size.is_empty() {
        return HttpResponse::BadRequest().json(serde_json::json!({"error": "Missing images or targetSize"}));
    }

    // Handle appendReverted logic
    let mut final_images = images_paths.clone();
    if append_reverted.to_lowercase() == "true" {
        let mut reversed = images_paths.clone();
        reversed.reverse();
        final_images.extend(reversed);
    }

    let output_path = format!("{}/output.gif", temp_dir.path().to_str().unwrap());

    // Construct ImageMagick command: convert -delay <ms*10> -loop 0 -resize <size> <files> <output>
    // Note: ImageMagick delay is in ticks (usually 1/100th of a second), so 100ms = 10 ticks.
    let delay_ticks = match delay.parse::<i32>() {
        Ok(d) => (d / 10).to_string(),
        Err(_) => "1".to_string(),
    };

    let mut cmd = Command::new("convert");
    cmd.arg("-delay").arg(delay_ticks);
    cmd.arg("-loop").arg("0");
    cmd.arg("-resize").arg(format!("{}!", target_size)); // Use ! to force exact dimensions
    
    for path in &final_images {
        cmd.arg(path);
    }
    
    cmd.arg(&output_path);

    match cmd.output() {
        Ok(out) if out.status.success() => {
            match std::fs::read(&output_path) {
                Ok(data) => HttpResponse::Ok().content_type("image/gif").body(data),
                Err(_) => HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to read generated GIF"})),
            }
        }
        Ok(out) => {
            let err = String::from_utf8_lossy(&out.stderr).to_string();
            HttpResponse::InternalServerError().json(serde_json::json!({"error": format!("ImageMagick error: {}", err)}))
        }
        Err(e) => HttpResponse::InternalServerError().json(serde_json::json!({"error": format!("Command execution failed: {}", e)})),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();
    
    HttpServer::new(|| {
        App::new()
            .service(create_gif)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}