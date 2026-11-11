use actix_multipart::{Field, Multipart};
use actix_web::{post, web, App, HttpResponse, HttpServer, Responder};
use futures_util::{StreamExt, TryStreamExt};
use serde::Serialize;
use std::io::Write;
use std::process::Command;
use uuid::Uuid;

#[derive(Serialize)]
struct ErrorResponse {
    error: String,
}

#[post("/extract")]
async fn extract_frame(mut payload: Multipart) -> impl Responder {
    let mut video_data: Vec<u8> = Vec::new();
    let mut frame_number: Option<i32> = None;
    let mut video_filename: Option<String> = None;

    // Process multipart stream
    while let Ok(Some(mut field)) = payload.try_next().await {
        let content_disposition = field.content_disposition();
        let name = content_disposition.get_parameter("name").unwrap_or("").to_string();

        match name.as_str() {
            "video" => {
                while let Ok(Some(chunk)) = field.try_next().await {
                    video_data.extend_from_slice(&chunk);
                }
            }
            "frameNumber" => {
                let mut bytes = Vec::new();
                while let Ok(Some(chunk)) = field.try_next().await {
                    bytes.extend_from_slice(&chunk);
                }
                if let Ok(val) = String::from_utf8(bytes).trim().parse::<i32>() {
                    frame_number = Some(val);
                }
            }
            "videoFileName" => {
                let mut bytes = Vec::new();
                while let Ok(Some(chunk)) = field.try_next().await {
                    bytes.extend_from_slice(&chunk);
                }
                if let Ok(val) = String::from_utf8(bytes).trim().to_string() {
                    video_filename = Some(val);
                }
            }
            _ => {
                // Skip unknown fields
                while let Ok(Some(_)) = field.try_next().await {}
            }
        }
    }

    let frame_idx = match frame_number {
        Some(f) => f,
        None => return HttpResponse::BadRequest().json("Missing frameNumber"),
    };

    if video_data.is_empty() {
        return HttpResponse::BadRequest().json("Missing video file");
    }

    // Use UUID to create unique temporary files for this request
    let request_id = Uuid::new_v4().to_string();
    let input_path = format!("/tmp/{}_{}", request_id, video_filename.unwrap_or_else(|| "video.mp4".to_string()));
    let output_path = format!("/tmp/{}_frame.png", request_id);

    // Write uploaded video to disk
    if let Err(e) = std::fs::write(&input_path, video_data) {
        return HttpResponse::InternalServerError().json(format!("Failed to save upload: {}", e));
    }

    // ffmpeg command: extract 1 frame at specific index
    // -i input, -vf "select=eq(n\,frame_number)" selects the frame, 
    // -vframes 1 ensures only one frame is outputted
    let status = Command::new("ffmpeg")
        .args([
            "-i", &input_path,
            "-vf", &format!("select=eq(n,{})", frame_idx),
            "-vframes", "1",
            "-q:v", "2",
            &output_path,
        ])
        .status();

    // Cleanup input file immediately
    let _ = std::fs::remove_file(&input_path);

    match status {
        Ok(s) if s.success() => {
            // Check if output file actually exists and has size (ffmpeg might succeed but not find the frame)
            if let Ok(metadata) = std::fs::metadata(&output_path) {
                if metadata.len() > 0 {
                    match std::fs::read(&output_path) {
                        Ok(img_bytes) => {
                            let _ = std::fs::remove_file(&output_path);
                            return HttpResponse::Ok()
                                .content_type("image/png")
                                .body(img_bytes);
                        }
                        Err(_) => {}
                    }
                }
            }
            
            let _ = std::fs::remove_file(&output_path);
            HttpResponse::NotFound().json(ErrorResponse {
                error: format!("Frame at index {} could not be found.", frame_idx),
            })
        }
        _ => {
            let _ = std::fs::remove_file(&output_path);
            HttpResponse::InternalServerError().json("FFmpeg processing failed")
        }
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();
    
    println!("Starting server on 0.0.0.0:5000...");
    
    HttpServer::new(|| {
        App::new()
            .service(extract_frame)
    })
    .bind("0.0.0.0:5000")?
    .run()
    .await
}