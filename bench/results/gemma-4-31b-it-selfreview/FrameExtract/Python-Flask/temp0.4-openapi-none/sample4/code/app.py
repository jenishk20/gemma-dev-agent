import os
import subprocess
import tempfile
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

# Resource exhaustion: Limit the maximum upload size (e.g., 100MB)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

@app.route('/extract', methods=['POST'])
def extract_frame():
    # Validate request content type
    if not request.is_json and not request.form:
        return jsonify({"error": "Invalid request. Expected multipart/form-data"}), 400

    # Extract parameters from multipart/form-data
    video_file = request.files.get('video')
    frame_number_raw = request.form.get('frameNumber')

    if not video_file or frame_number_raw is None:
        return jsonify({"error": "Missing required fields: video or frameNumber"}), 400

    # Resource exhaustion / Input validation: Ensure frameNumber is a positive integer
    try:
        frame_idx = int(frame_number_raw)
        if frame_idx < 0:
            return jsonify({"error": "Frame index must be non-negative"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "frameNumber must be an integer"}), 400

    # Use a temporary directory to handle the upload and the output frame
    # This prevents path traversal as we define the filenames ourselves
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # We use hardcoded filenames inside the secure temp directory
            # to prevent untrusted input from reaching a file path.
            video_path = os.path.join(tmpdir, "input_video.tmp")
            output_path = os.path.join(tmpdir, "frame.png")

            # Save the uploaded video to disk
            video_file.save(video_path)

            # Shell Injection Prevention: 
            # We use a list for subprocess.run, which avoids shell=True.
            # The frame_idx is cast to int, preventing injection via the filter string.
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vf', f'select=eq(n\\,{frame_idx})',
                '-vframes', '1',
                '-f', 'image2',
                output_path
            ]

            try:
                # Resource exhaustion: timeout prevents hanging processes
                # stderr=subprocess.PIPE prevents leaking ffmpeg logs to the console/logs
                result = subprocess.run(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    timeout=30,
                    shell=False 
                )
                
                # Check if the output file was actually created and ffmpeg succeeded
                if result.returncode != 0 or not os.path.exists(output_path):
                    return jsonify({"error": f"Frame at index {frame_idx} could not be found."}), 404

                # Return the extracted image as a PNG
                return send_file(output_path, mimetype='image/png')

            except subprocess.TimeoutExpired:
                return jsonify({"error": "Processing timed out"}), 500
            except Exception:
                # Error handling: Generic error to avoid leaking internal stack traces
                return jsonify({"error": "An internal error occurred during processing"}), 500

    except Exception:
        return jsonify({"error": "An internal error occurred"}), 500

if __name__ == '__main__':
    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)