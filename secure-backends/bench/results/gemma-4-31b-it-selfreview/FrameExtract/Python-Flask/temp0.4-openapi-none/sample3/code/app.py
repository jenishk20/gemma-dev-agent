import os
import subprocess
import tempfile
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

# Resource Exhaustion: Limit the maximum allowed upload size (e.g., 100MB)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

@app.route('/extract', methods=['POST'])
def extract_frame():
    # Parse multipart/form-data
    video_file = request.files.get('video')
    frame_number = request.form.get('frameNumber')
    
    if not video_file or frame_number is None:
        return jsonify({"error": "Missing video file or frameNumber"}), 400

    try:
        # Validate frame_number is a non-negative integer to prevent 
        # unexpected behavior in ffmpeg filter strings
        frame_idx = int(frame_number)
        if frame_idx < 0:
            return jsonify({"error": "Frame index must be non-negative"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "frameNumber must be an integer"}), 400

    # Use a temporary directory to isolate files
    # tempfile.TemporaryDirectory is secure and handles cleanup
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Path Traversal Prevention: 
            # We ignore the user-provided 'videoFileName' for the actual filesystem path
            # and use a hardcoded filename inside the secure temp directory.
            video_path = os.path.join(tmpdir, "input_video.tmp")
            output_path = os.path.join(tmpdir, "frame.png")
            
            # Save the uploaded video to disk
            video_file.save(video_path)

            # Command Injection Prevention:
            # Use a list for subprocess.run (shell=False by default).
            # This ensures arguments are passed directly to the execve system call,
            # preventing shell metacharacter injection.
            # We use a strict format for the filter string.
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vf', f'select=eq(n\,{frame_idx})',
                '-vframes', '1',
                '-f', 'image2',
                output_path
            ]

            # Resource Exhaustion: Add a timeout to prevent long-running processes
            # from hanging the server (e.g., 30 seconds).
            process = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            if process.returncode != 0 or not os.path.exists(output_path):
                return jsonify({"error": f"Frame at index {frame_idx} could not be found."}), 404
            
            # Return the extracted image. 
            # send_file is used here; since output_path is controlled by us, it's safe.
            return send_file(output_path, mimetype='image/png')
            
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Processing timed out"}), 500
    except Exception:
        # Error Handling: Catch all other exceptions to prevent leaking stack traces
        # and return a generic 500 error.
        return jsonify({"error": "An internal error occurred"}), 500

if __name__ == '__main__':
    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)