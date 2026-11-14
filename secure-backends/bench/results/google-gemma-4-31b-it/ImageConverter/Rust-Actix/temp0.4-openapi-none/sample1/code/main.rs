use actix_multipart::{Field, Multipart};
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
        Err(_) => return HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to create temp directory"})),
    };

    let mut images_paths = Vec::new();
    let mut target_size: Option<String> = None;
    let mut delay: Option<i32> = None;
    let mut append_reverted: bool = false;

    while let Ok(Some(mut field)) = payload.try_next().await {
        let content_disposition = field.content_disposition();
        let name = content_disposition.get_parameter("name").unwrap_or("");

        if name == "images" {
            let filename = format!("{}.tmp", Uuid::new_v4());
            let path = temp_dir.path().join(&filename);
            let mut f = match File::create(&path) {
                Ok(file) => file,
                Err(_) => return HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to create temp file"})),
            };

            while let Ok(Some(chunk)) = field.try_next().await {
                if let Err(_) = f.write_all(&chunk) {
                    return HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to write image chunk"}));
                }
            }
            images_paths.push(path);
        } else if name == "targetSize" {
            let mut bytes = Vec::new();
            while let Ok(Some(chunk)) = field.try_next().await {
                bytes.extend_from_slice(&chunk);
            }
            target_size = Some(String::from_utf8_lossy(&bytes).to_string());
        } else if name == "delay" {
            let mut bytes = Vec::new();
            while let Ok(Some(chunk)) = field.try_next().await {
                bytes.extend_from_slice(&chunk);
            }
            delay = String::from_utf8_lossy(&bytes).parse::<i32>().ok();
        } else if name == "appendReverted" {
            let mut bytes = Vec::new();
            while let Ok(Some(chunk)) = field.try_next().await {
                bytes.extend_from_slice(&chunk);
            }
            let val = String::from_utf8_lossy(&bytes).to_lowercase();
            append_reverted = val == "true" || val == "1";
        }
    }

    if images_paths.is_empty() {
        return HttpResponse::BadRequest().json(serde_json::json!({"error": "No images provided"}));
    }

    let size = match target_size {
        Some(s) => s,
        None => return HttpResponse::BadRequest().json(serde_json::json!({"error": "targetSize is required"})),
    };

    let delay_val = delay.unwrap_or(10);
    let output_path = temp_dir.path().join("output.gif");

    // Build ImageMagick command
    // convert -delay <ms/10> -loop 0 -resize <size> <images...> <reverted_images...> output.gif
    // Note: ImageMagick -delay is in ticks (usually 1/100th of a second). 
    // The schema says milliseconds. 100ms = 10 ticks.
    let delay_ticks = delay_val / 10;

    let mut cmd = Command::new("convert");
    cmd.arg("-delay").arg(delay_ticks.to_string());
    cmd.arg("-loop").arg("0");
    cmd.arg("-resize").arg(size);

    for path in &images_paths {
        cmd.arg(path.to_str().unwrap());
    }

    if append_reverted {
        for path in images_paths.iter().rev().skip(1) {
            cmd.arg(path.to_str().unwrap());
        }
    }

    cmd.arg(output_path.to_str().unwrap());

    if let Err(e) = cmd.output() {
        return HttpResponse::InternalServerError().json(serde_json::json!({"error": format!("ImageMagick error: {}", e)}));
    }

    match std::fs::read(&output_path) {
        Ok(content) => HttpResponse::Ok()
            .content_type("image/gif")
            .body(content),
        Err(_) => HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to read output GIF"})),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();
    
    HttpServer::new(|| {
        App::new().service(create_gif)
    })
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}