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
    let temp_dir = match TempDir::new() {
        Ok(dir) => dir,
        Err(_) => return HttpResponse::InternalServerError().body("Failed to create temp directory"),
    };

    let mut video_path = String::new();
    let mut frame_number: Option<i32> = None;
    let mut video_file_name = String::new();

    // Iterate over multipart form fields
    while let Ok(Some(mut field)) = payload.try_next().await {
        let content_disposition = field.content_disposition();
        let name = content_disposition.get_name().unwrap_or("");

        match name {
            "videoFileName" => {
                let mut bytes = Vec::new();
                while let Ok(Some(chunk)) = field.try_next().await {
                    bytes.extend_from_slice(&chunk);
                }
                video_file_name = String::from_utf8_lossy(&bytes).to_string();
            }
            "frameNumber" => {
                let mut bytes = Vec::new();
                while let Ok(Some(chunk)) = field.try_next().await {
                    bytes.extend_from_slice(&chunk);
                }
                frame_number = String::from_utf8_lossy(&bytes).trim().parse::<i32>().ok();
            }
            "video" => {
                let request_id = Uuid::new_v4().to_string();
                let file_path = temp_dir.path().join(format!("{}.tmp", request_id));
                let mut f = match File::create(&file_path) {
                    Ok(file) => file,
                    Err(_) => return HttpResponse::InternalServerError().body("File creation failed"),
                };

                while let Ok(Some(chunk)) = field.try_next().await {
                    if let Err(_) = f.write_all(&chunk) {
                        return HttpResponse::InternalServerError().body("Failed to write video file");
                    }
                }
                video_path = file_path.to_string_lossy().to_string();
            }
            _ => {}
        }
    }

    let frame_idx = match frame_number {
        Some(n) => n,
        None => return HttpResponse::BadRequest().json(serde_json::json!({"error": "frameNumber is required"})),
    };

    if video_path.is_empty() {
        return HttpResponse::BadRequest().json(serde_json::json!({"error": "video file is required"}));
    }

    // Output image path
    let output_image_path = temp_dir.path().join("output.png");

    // ffmpeg -i <input> -vf "select=eq(n\<frame_number>)" -vframes 1 <output>
    // Note: frame index in ffmpeg select filter is 0-based.
    let status = Command::new("ffmpeg")
        .arg("-i")
        .arg(&video_path)
        .arg("-vf")
        .arg(format!("select=eq(n,{})", frame_idx))
        .arg("-vframes")
        .arg("1")
        .arg("-y") // overwrite
        .arg(&output_image_path)
        .status();

    match status {
        Ok(s) if s.success() => {
            match std::fs::read(&output_image_path) {
                Ok(img_data) => HttpResponse::Ok()
                    .content_type("image/png")
                    .body(img_data),
                Err(_) => HttpResponse::InternalServerError().body("Failed to read extracted frame"),
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
    env_logger::init_from_env(env_logger::Env::new().default_filter_or("info"));

    HttpServer::new(|| {
        App::new().service(extract_frame)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}