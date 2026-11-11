use actix_multipart::Multipart;
use actix_web::{post, web, App, HttpResponse, HttpServer, Responder};
use futures_util::{StreamExt, TryStreamExt};
use std::fs::File;
use std::io::Write;
use std::process::Command;
use tempdir::TempDir;
use uuid::Uuid;

#[derive(serde::Deserialize)]
struct ExtractParams {
    frame_number: i32,
}

#[post("/extract")]
async fn extract_frame(mut payload: Multipart) -> impl Responder {
    let temp_dir = TempDir::new().expect("Failed to create temp dir");
    let session_id = Uuid::new_v4().to_string();
    
    let mut video_path = String::new();
    let mut frame_number: Option<i32> = None;

    // Process multipart form data
    while let Ok(Some(mut field)) = payload.try_next().await {
        let content_disposition = field.content_disposition();
        let name = content_disposition.get_name().unwrap_or("");

        if name == "video" {
            let file_path = format!("{}/video_{}.mp4", temp_dir.path().to_str().unwrap(), session_id);
            let mut f = File::create(&file_path).expect("Failed to create file");
            
            while let Some(chunk) = field.next().await {
                let data = chunk.unwrap();
                f.write_all(&data).unwrap();
            }
            video_path = file_path;
        } else if name == "frameNumber" {
            let mut bytes = web::BytesMut::new();
            while let Some(chunk) = field.next().await {
                bytes.extend_from_slice(&chunk.unwrap());
            }
            if let Ok(num) = std::str::from_utf8(&bytes).unwrap_or("").trim().parse::<i32>() {
                frame_number = Some(num);
            }
        }
    }

    let frame_idx = match frame_number {
        Some(n) => n,
        None => return HttpResponse::BadRequest().json(serde_json::json!({"error": "frameNumber is required"})),
    };

    if video_path.is_empty() {
        return HttpResponse::BadRequest().json(serde_json::json!({"error": "video file is required"}));
    }

    let output_path = format!("{}/frame_{}.png", temp_dir.path().to_str().unwrap(), session_id);

    // ffmpeg -i input.mp4 -vf "select=eq(n\,FRAME_INDEX)" -vframes 1 output.png
    let status = Command::new("ffmpeg")
        .args([
            "-i", &video_path,
            "-vf", &format!("select=eq(n\\,{})", frame_idx),
            "-vframes", "1",
            "-y",
            &output_path,
        ])
        .status();

    match status {
        Ok(s) if s.success() => {
            // Check if file was actually created (ffmpeg sometimes returns 0 even if frame is out of range)
            if std::path::Path::new(&output_path).exists() {
                match std::fs::read(&output_path) {
                    Ok(img_data) => HttpResponse::Ok().content_type("image/png").body(img_data),
                    Err(_) => HttpResponse::InternalServerError().finish(),
                }
            } else {
                HttpResponse::NotFound().json(serde_json::json!({
                    "error": format!("Frame at index {} could not be found.", frame_idx)
                }))
            }
        }
        _ => HttpResponse::NotFound().json(serde_json::json!({
            "error": format!("Frame at index {} could not be found.", frame_idx)
        })),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();
    
    HttpServer::new(|| {
        App::new().service(extract_frame)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}