use actix_multipart::Multipart;
use actix_web::{post, web, App, HttpResponse, HttpServer, Responder};
use futures_util::StreamExt;
use std::fs::{self, File};
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

    let mut image_paths = Vec::new();
    let mut target_size: Option<String> = None;
    let mut delay: Option<i32> = None;
    let mut append_reverted: bool = false;

    // Process multipart stream
    while let Some(item) = payload.next().await {
        let mut field = match item {
            Ok(f) => f,
            Err(_) => return HttpResponse::BadRequest().json(serde_json::json!({"error": "Multipart error"})),
        };

        let content_disposition = field.content_disposition();
        let name = content_disposition.get_parameter("name").unwrap_or("").to_string();

        if name == "images" {
            let file_id = Uuid::new_v4().to_string();
            let file_path = format!("{}/{}.tmp", temp_dir.path().to_str().unwrap(), file_id);
            let mut f = File::create(&file_path).unwrap();
            
            while let Some(chunk) = field.next().await {
                let data = match chunk {
                    Ok(d) => d,
                    Err(_) => return HttpResponse::BadRequest().json(serde_json::json!({"error": "Error reading image chunk"})),
                };
                f.write_all(&data).unwrap();
            }
            image_paths.push(file_path);
        } else if name == "targetSize" {
            let mut bytes = web::BytesMut::new();
            while let Some(chunk) = field.next().await {
                let data = match chunk {
                    Ok(d) => d,
                    Err(_) => return HttpResponse::BadRequest().json(serde_json::json!({"error": "Error reading targetSize"})),
                };
                bytes.extend_from_slice(&data);
            }
            target_size = Some(String::from_utf8_lossy(&bytes).to_string());
        } else if name == "delay" {
            let mut bytes = web::BytesMut::new();
            while let Some(chunk) = field.next().await {
                let data = match chunk {
                    Ok(d) => d,
                    Err(_) => return HttpResponse::BadRequest().json(serde_json::json!({"error": "Error reading delay"})),
                };
                bytes.extend_from_slice(&data);
            }
            delay = String::from_utf8_lossy(&bytes).parse::<i32>().ok();
        } else if name == "appendReverted" {
            let mut bytes = web::BytesMut::new();
            while let Some(chunk) = field.next().await {
                let data = match chunk {
                    Ok(d) => d,
                    Err(_) => return HttpResponse::BadRequest().json(serde_json::json!({"error": "Error reading appendReverted"})),
                };
                bytes.extend_from_slice(&data);
            }
            let val = String::from_utf8_lossy(&bytes).to_lowercase();
            append_reverted = val == "true";
        }
    }

    if image_paths.is_empty() || target_size.is_none() {
        return HttpResponse::BadRequest().json(serde_json::json!({"error": "images and targetSize are required"}));
    }

    let size = target_size.unwrap();
    let d_val = delay.unwrap_or(10);
    let output_path = format!("{}/output.gif", temp_dir.path().to_str().unwrap());

    // Prepare image list for ImageMagick
    let mut input_files = image_paths.clone();
    if append_reverted {
        let mut reversed = image_paths.clone();
        reversed.reverse();
        input_files.extend(reversed);
    }

    // Construct ImageMagick command: convert -delay 10 -size 500x500 img1 img2 ... output.gif
    // Note: -resize is usually better for targetSize in ImageMagick
    let mut cmd = Command::new("convert");
    cmd.arg("-delay").arg(d_val.to_string());
    cmd.arg("-resize").arg(size);
    for path in &input_files {
        cmd.arg(path);
    }
    cmd.arg(output_path.clone());

    if let Err(e) = cmd.status() {
        return HttpResponse::InternalServerError().json(serde_json::json!({"error": format!("ImageMagick error: {}", e)}));
    }

    match fs::read(output_path) {
        Ok(content) => HttpResponse::Ok().content_type("image/gif").body(content),
        Err(_) => HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to read generated GIF"})),
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