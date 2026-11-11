import os
import subprocess
import tempfile
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

# Resource exhaustion: Limit the maximum upload size to 100MB
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

@app.route('/extract', methods=['POST'])
def extract_frame():
    # Validate multipart/form-data
    if not request.files or 'video' not in request.files:
        return jsonify({"error": "Missing video file"}), 400

    video_file = request.files['video']
    frame_number = request.form.get('frameNumber')
    
    if frame_number is None:
        return jsonify({"error": "Missing frameNumber"}), 400
    
    try:
        # Validate frame_number is a non-negative integer to prevent injection/logic errors
        frame_index = int(frame_number)
        if frame_index < 0:
            return jsonify({"error": "Frame index must be non-negative"}), 400
    except ValueError:
        return jsonify({"error": "frameNumber must be an integer"}), 400

    # Use a temporary directory to ensure isolation and prevent path traversal
    # tempfile.TemporaryDirectory is secure and creates a unique path
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # We ignore 'videoFileName' from the request for the actual filesystem path 
            # to prevent path traversal attacks. We use a fixed internal name.
            video_path = os.path.join(tmpdir, "input_video")
            output_path = os.path.join(tmpdir, "frame.png")
            
            # Save the uploaded video
            video_file.save(video_path)

            # Use subprocess.run with a list of arguments (shell=False by default)
            # This prevents shell injection.
            # The frame_index is cast to int, ensuring no malicious strings reach the command.
            try:
                cmd = [
                    'ffmpeg',
                    '-i', video_path,
                    '-vf', f'select=eq(n\\{,} {frame_index})',
                    '-vframes', '1',
                    '-f', 'image2',
                    output_path
                ]
                
                # Added a timeout to prevent resource exhaustion (DoS) via long-running ffmpeg processes
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=30,
                    check=False 
                )
                
                if result.returncode != 0 or not os.path.exists(output_path):
                    return jsonify({"error": f"Frame at index {frame_index} could not be found."}), 404
                
                # Return the extracted image as a PNG
                return send_file(output_path, mimetype='image/png')
                
            except subprocess.TimeoutExpired:
                return jsonify({"error": "Processing timed out"}), 500
            except Exception:
                # Generic error to avoid leaking internal stack traces
                return jsonify({"error": "An internal error occurred during extraction"}), 500
                
    except Exception:
        return jsonify({"error": "An internal error occurred"}), 500

if __name__ == '__main__':
    # Start the webserver on port 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)