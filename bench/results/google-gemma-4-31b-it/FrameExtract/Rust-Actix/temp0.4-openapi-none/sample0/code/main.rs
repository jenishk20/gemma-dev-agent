use actix_multipart::Multipart;
use actix_web::{post, web, App, HttpResponse, HttpServer, Responder};
use futures_util::{StreamExt, TryStreamExt};
use serde::Serialize;
use std::io::Write;
use std::process::Command;
use tempdir::TempDir;
use uuid::Uuid;

#[derive(Serialize)]
struct ErrorResponse {
    error: String,
}

#[post("/extract")]
async fn extract_frame(mut payload: Multipart) -> impl Responder {
    let temp_dir = TempDir::new().expect("Failed to create temp dir");
    let session_id = Uuid::new_v4().to_string();
    
    let mut video_path: Option<String> = None;
    let mut frame_number: Option<i32> = None;

    // Process multipart form data
    while let Some(field) = payload.next().await {
        let field = match field {
            Ok(f) => f,
            Err(_) => return HttpResponse::BadRequest().body("Multipart error"),
        };

        let content_disposition = field.content_disposition();
        let name = content_disposition.get_name().unwrap_or("");

        match name {
            "frameNumber" => {
                let mut bytes = Vec::new();
                let mut stream = field;
                while let Some(chunk) = stream.next().await {
                    if let Ok(data) = chunk {
                        bytes.extend_from_slice(&data);
                    }
                }
                let s = String::from_utf8_lossy(&bytes);
                frame_number = s.trim().parse::<i32>().ok();
            }
            "video" => {
                let file_path = temp_dir.path().join(format!("{}.tmp", session_id));
                let mut f = std::fs::File::create(&file_path).expect("Failed to create file");
                let mut stream = field;
                while let Some(chunk) = stream.next().await {
                    if let Ok(data) = chunk {
                        f.write_all(&data).expect("Failed to write video chunk");
                    }
                }
                video_path = Some(file_path.to_string_lossy().into_owned());
            }
            _ => {
                // Ignore other fields like videoFileName
                let mut stream = field;
                while let Some(_) = stream.next().await {}
            }
        }
    }

    let video_path = match video_path {
        Some(p) => p,
        None => return HttpResponse::BadRequest().json(ErrorResponse { error: "Missing video file".to_string() }),
    };

    let frame_idx = match frame_number {
        Some(n) => n,
        None => return HttpResponse::BadRequest().json(ErrorResponse { error: "Missing frameNumber".to_string() }),
    };

    let output_path = temp_dir.path().join(format!("{}.png", session_id));

    // ffmpeg command: -i <input> -vf "select=K=N" -vframes 1 <output>
    // Note: select=K=N selects the N-th frame.
    let status = Command::new("ffmpeg")
        .args([
            "-i", &video_path,
            "-vf", &format!("select=eq(n,{})", frame_idx),
            "-vframes", "1",
            "-f", "image2",
            output_path.to_str().unwrap(),
        ])
        .status()
        .expect("Failed to execute ffmpeg");

    if status.success() && output_path.exists() {
        match std::fs::read(&output_path) {
            Ok(data) => HttpResponse::Ok().content_type("image/png").body(data),
            Err(_) => HttpResponse::InternalServerError().finish(),
        }
    } else {
        HttpResponse::NotFound().json(ErrorResponse {
            error: format!("Frame at index {} could not be found.", frame_idx),
        })
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();
    
    HttpServer::new(|| {
        App::new().service(extract_frame)
    })
    .bind(("0.0.0.0", 5000))?
    .run()
    .await
}