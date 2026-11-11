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
        Err(_) => return HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to create temp directory"})),
    };

    let mut images_paths = Vec::new();
    let mut target_size = String::new();
    let mut delay = "10".to_string();
    let mut append_reverted = "false".to_string();

    // Process multipart stream
    while let Ok(Some(mut field)) = payload.try_next().await {
        let content_disposition = field.content_disposition();
        let name = content_disposition.get_parameter_name().unwrap_or("");

        match name {
            "images" => {
                let file_id = Uuid::new_v4().to_string();
                let file_path = format!("{}/{}.tmp", temp_dir.path().to_str().unwrap(), file_id);
                let mut f = File::create(&file_path).unwrap();
                
                while let Ok(Some(chunk)) = field.try_next().await {
                    f.write_all(&chunk).unwrap();
                }
                images_paths.push(file_path);
            }
            "targetSize" => {
                while let Ok(Some(chunk)) = field.try_next().await {
                    target_size.push_str(std::str::from_utf8(&chunk).unwrap_or(""));
                }
            }
            "delay" => {
                while let Ok(Some(chunk)) = field.try_next().await {
                    delay.push_str(std::str::from_utf8(&chunk).unwrap_or(""));
                }
            }
            "appendReverted" => {
                while let Ok(Some(chunk)) = field.try_next().await {
                    append_reverted.push_str(std::str::from_utf8(&chunk).unwrap_or(""));
                }
            }
            _ => {}
        }
    }

    if images_paths.is_empty() || target_size.is_empty() {
        return HttpResponse::BadRequest().json(serde_json::json!({"error": "Missing images or targetSize"}));
    }

    let output_path = format!("{}/output.gif", temp_dir.path().to_str().unwrap());
    
    // Construct ImageMagick command
    // convert -delay [ms/10] -loop 0 -resize [size] [images] [reverted_images] output.gif
    // Note: ImageMagick delay is in ticks (1/100th of a second), so ms / 10
    let delay_ticks = delay.parse::<i32>().unwrap_or(10) / 10;
    
    let mut args = vec![];
    args.push("-delay".to_string());
    args.push(delay_ticks.to_string());
    args.push("-loop".to_string());
    args.push("0".to_string());
    args.push("-resize".to_string());
    args.push(target_size.clone());

    // Add forward images
    for path in &images_paths {
        args.push(path.clone());
    }

    // Add reverted images if requested
    if append_reverted.to_lowercase() == "true" {
        for path in images_paths.iter().rev() {
            args.push(path.clone());
        }
    }

    args.push(output_path.clone());

    let status = Command::new("convert")
        .args(&args)
        .status();

    match status {
        Ok(s) if s.success() => {
            match std::fs::read(output_path) {
                Ok(data) => HttpResponse::Ok()
                    .content_type("image/gif")
                    .body(data),
                Err(_) => HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to read generated GIF"})),
            }
        }
        _ => HttpResponse::InternalServerError().json(serde_json::json!({"error": "ImageMagick conversion failed"})),
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