import os
import subprocess
import tempfile
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

# Resource exhaustion: Limit the maximum upload size (e.g., 100MB)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

@app.route('/extract', methods=['POST'])
def extract_frame():
    # Validate multipart/form-data
    if not request.files or 'video' not in request.files:
        return jsonify({"error": "Missing video file"}), 400

    video_file = request.files['video']
    # Get frameNumber from form data
    frame_number_str = request.form.get('frameNumber')
    
    if frame_number_str is None:
        return jsonify({"error": "Missing frameNumber"}), 400
    
    try:
        # Validate frameNumber is a non-negative integer to prevent 
        # potential logic errors or unexpected ffmpeg behavior
        frame_number = int(frame_number_str)
        if frame_number < 0:
            return jsonify({"error": f"Frame at index {frame_number} could not be found."}), 404
    except ValueError:
        return jsonify({"error": "frameNumber must be an integer"}), 400

    # Use a temporary directory to handle the upload and output
    # This prevents path traversal as we define the filenames ourselves
    # and do not use user-supplied 'videoFileName' for filesystem operations.
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "input_video")
        output_path = os.path.join(tmpdir, "output_frame.png")
        
        try:
            # Save the uploaded video to disk
            video_file.save(video_path)

            # Security: Use a list for subprocess.run to avoid shell=True.
            # This prevents shell injection.
            # We use hardcoded filenames within the tmpdir, ignoring the 
            # user-provided 'videoFileName' to prevent path traversal.
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vf', f'select=eq(n,{frame_number})',
                '-vframes', '1',
                '-f', 'image2',
                output_path,
                '-y' 
            ]

            # Resource exhaustion: Add a timeout to prevent hanging processes
            process = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=30 
            )
            
            # Check if the output file was actually created and process succeeded
            if process.returncode != 0 or not os.path.exists(output_path):
                return jsonify({"error": f"Frame at index {frame_number} could not be found."}), 404
            
            # Return the image file
            return send_file(output_path, mimetype='image/png')
            
        except subprocess.TimeoutExpired:
            return jsonify({"error": "Processing timed out"}), 500
        except Exception:
            # Error handling: Return a generic error to avoid leaking internal stack traces
            return jsonify({"error": "An internal error occurred"}), 500

if __name__ == '__main__':
    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)