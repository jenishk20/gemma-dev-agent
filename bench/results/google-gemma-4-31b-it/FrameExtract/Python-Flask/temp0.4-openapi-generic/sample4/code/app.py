import os
import subprocess
import tempfile
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

# Security: Limit upload size to prevent DoS (e.g., 100MB)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

@app.route('/extract', methods=['POST'])
def extract_frame():
    """
    Extracts a specific frame from an uploaded video using ffmpeg.
    """
    # Validate request content type
    if not request.content_type == 'multipart/form-data':
        return jsonify({"error": "Invalid content type. Expected multipart/form-data"}), 400

    # Extract parameters from form
    video_file = request.files.get('video')
    frame_number_str = request.form.get('frameNumber')
    
    # Basic validation
    if not video_file or not frame_number_str:
        return jsonify({"error": "Missing required fields: video or frameNumber"}), 400

    try:
        frame_number = int(frame_number_str)
    except ValueError:
        return jsonify({"error": "frameNumber must be an integer"}), 400

    # Use a temporary directory to handle the file securely
    with tempfile.TemporaryDirectory() as tmpdir:
        # Securely save the uploaded file
        # We ignore the provided 'videoFileName' for the actual filesystem path to avoid path traversal
        input_path = os.path.join(tmpdir, "input_video")
        video_file.save(input_path)
        
        output_path = os.path.join(tmpdir, "frame.png")

        # ffmpeg command:
        # -i: input file
        # -vf "select=eq(n\,FRAME_INDEX)": filter to select the specific frame index
        # -vframes 1: output only one frame
        # -f image2: force image format
        try:
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-vf', f'select=eq(n\\,{frame_number})',
                '-vframes', '1',
                '-f', 'image2',
                output_path
            ]
            
            # Run ffmpeg. stderr is captured to check for errors.
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Check if the file was actually created (ffmpeg might return 0 even if no frame was found)
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                return jsonify({"error": f"Frame at index {frame_number} could not be found."}), 404

            # Return the image file
            return send_file(output_path, mimetype='image/png')

        except subprocess.CalledProcessError as e:
            # Log the error internally and return 404 as per schema if frame is missing
            return jsonify({"error": f"Frame at index {frame_number} could not be found."}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)