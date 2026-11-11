use actix_multipart::Multipart;
use actix_web::{post, web, App, HttpResponse, HttpServer, Responder};
use futures_util::{StreamExt, TryStreamExt};
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
    let mut target_size: Option<String> = None;
    let mut delay: Option<i32> = None;
    let mut append_reverted: bool = false;

    // Process multipart form data
    while let Ok(Some(mut field)) = payload.try_next().await {
        let content_disposition = field.content_disposition();
        let name = content_disposition.get_parameter("name").unwrap_or("").to_string();

        if name == "images" {
            let filename = format!("{}.tmp", Uuid::new_v4());
            let path = temp_dir.path().join(filename);
            let mut f = match std::fs::File::create(&path) {
                Ok(file) => file,
                Err(_) => return HttpResponse::InternalServerError().json(serde_json::json!({"error": "File creation failed"})),
            };

            while let Ok(Some(chunk)) = field.try_next().await {
                if let Err(_) = f.write_all(&chunk) {
                    return HttpResponse::InternalServerError().json(serde_json::json!({"error": "Write failed"}));
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
    let target_size = match target_size {
        Some(s) => s,
        None => return HttpResponse::BadRequest().json(serde_json::json!({"error": "targetSize is required"}));
    };

    let delay_val = delay.unwrap_or(10);
    let output_path = temp_dir.path().join("result.gif");

    // Build ImageMagick command
    // convert -delay 10 -size 500x500 img1.jpg img2.jpg -duplicate 0,1 result.gif
    // Note: To handle "appendReverted", we can list the images in reverse order after the original set.
    let mut args = vec!["-delay".to_string(), delay_val.to_string()];
    args.push("-resize".to_string());
    args.push(target_size);

    for path in &images_paths {
        args.push(path.to_string_lossy().to_string());
    }

    if append_reverted {
        for path in images_paths.iter().rev().skip(1) {
            args.push(path.to_string_lossy().to_string());
        }
    }

    args.push(output_path.to_string_lossy().to_string());

    let status = Command::new("convert")
        .args(&args)
        .status();

    match status {
        Ok(s) if s.success() => {
            match std::fs::read(&output_path) {
                Ok(content) => HttpResponse::Ok()
                    .content_type("image/gif")
                    .body(content),
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
        App::new().service(create_gif)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}