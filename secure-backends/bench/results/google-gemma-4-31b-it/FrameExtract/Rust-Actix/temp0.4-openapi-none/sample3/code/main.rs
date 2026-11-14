use actix_multipart::Multipart;
use actix_web::{post, App, HttpResponse, HttpServer, Responder};
use futures_util::{StreamExt, TryStreamExt};
use std::fs::File;
use std::io::Write;
use std::process::Command;
use tempdir::TempDir;
use uuid::Uuid;

#[post("/extract")]
async fn extract_frame(mut payload: Multipart) -> impl Responder {
    let temp_dir = TempDir::new().expect("Failed to create temp dir");
    let session_id = Uuid::new_v4().to_string();
    
    let mut video_path = String::new();
    let mut frame_number: Option<i32> = None;

    // Iterate over the multipart form data
    while let Ok(Some(mut field)) = payload.try_next().await {
        let content_disposition = field.content_disposition();
        let name = content_disposition.get_name().unwrap_or("");

        match name {
            "video" => {
                let file_path = format!("{}/video_{}.mp4", temp_dir.path().to_str().unwrap(), session_id);
                let mut f = File::create(&file_path).expect("Failed to create file");
                while let Ok(Some(chunk)) = field.try_next().await {
                    f.write_all(&chunk).expect("Failed to write chunk");
                }
                video_path = file_path;
            }
            "frameNumber" => {
                let mut bytes = Vec::new();
                while let Ok(Some(chunk)) = field.try_next().await {
                    bytes.extend_from_slice(&chunk);
                }
                if let Ok(s) = String::from_utf8(bytes) {
                    frame_number = s.trim().parse::<i32>().ok();
                }
            }
            _ => {
                // Skip other fields like videoFileName
                while let Ok(Some(_)) = field.try_next().await {}
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

    let output_image_path = format!("{}/frame_{}.png", temp_dir.path().to_str().unwrap(), session_id);

    // ffmpeg command: -i input -vf "select=eq(n,FRAME_INDEX)" -vframes 1 output.png
    let status = Command::new("ffmpeg")
        .arg("-i")
        .arg(&video_path)
        .arg("-vf")
        .arg(format!("select=eq(n,{})", frame_idx))
        .arg("-vframes")
        .arg("1")
        .arg("-f")
        .arg("image2")
        .arg(&output_image_path)
        .status();

    match status {
        Ok(s) if s.success() => {
            match std::fs::read(&output_image_path) {
                Ok(img_data) => {
                    // We must keep the temp_dir alive until we read the file.
                    // Since temp_dir is dropped at the end of this function, 
                    // the file is read into memory first.
                    HttpResponse::Ok()
                        .content_type("image/png")
                        .body(img_data)
                }
                Err(_) => HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to read extracted frame"})),
            }
        }
        _ => {
            HttpResponse::NotFound().json(serde_json::json!({
                "error": format!("Frame at index {} could not be found.", frame_idx)
            }))
        }
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();
    
    println!("Starting server at http://0.0.0.0:5000");
    HttpServer::new(|| {
        App::new().service(extract_frame)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}