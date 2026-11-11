import os
import subprocess
import tempfile
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

# Resource exhaustion: Limit the maximum size of the uploaded file (e.g., 100MB)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

@app.route('/extract', methods=['POST'])
def extract_frame():
    # Extracting parameters from multipart/form-data
    video_file = request.files.get('video')
    frame_number = request.form.get('frameNumber')
    
    # Basic validation for presence of required fields
    if not video_file or frame_number is None:
        return jsonify({"error": "Missing video file or frameNumber"}), 400

    # Resource exhaustion & Input validation: Ensure frameNumber is a non-negative integer
    try:
        frame_idx = int(frame_number)
        if frame_idx < 0:
            return jsonify({"error": "Frame index must be non-negative"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "frameNumber must be an integer"}), 400

    # Use a temporary directory to isolate files and prevent path traversal
    # tempfile.TemporaryDirectory() creates a secure, unique directory
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # We define fixed filenames inside the secure tmpdir to avoid 
            # using user-supplied 'videoFileName' in the filesystem path.
            video_path = os.path.join(tmpdir, "input_video.tmp")
            output_path = os.path.join(tmpdir, "frame.png")
            
            # Save the uploaded video. Flask's save() handles the stream.
            video_file.save(video_path)
            
            # Security: Use a list for subprocess.run to avoid shell=True.
            # This prevents shell injection.
            # We use a specific filter string. Since frame_idx is cast to int, 
            # it cannot contain malicious shell characters.
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vf', f'select=eq(n,{frame_idx})',
                '-vframes', '1',
                '-f', 'image2',
                output_path
            ]
            
            # Resource exhaustion: Add a timeout to prevent long-running processes
            # from hanging the server (e.g., 30 seconds).
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            if result.returncode != 0 or not os.path.exists(output_path):
                # Return the documented 404 error for frames not found
                return jsonify({"error": f"Frame at index {frame_idx} could not be found."}), 404
            
            # Return the extracted image. 
            # send_file is used with a path inside the secure tmpdir.
            return send_file(output_path, mimetype='image/png')
            
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Processing timed out"}), 500
    except Exception:
        # Error handling: Return a generic 500 error without leaking stack traces
        return jsonify({"error": "An internal error occurred"}), 500

if __name__ == '__main__':
    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)